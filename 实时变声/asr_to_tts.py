#!/usr/bin/env python3
"""
阿里云ASR → 火山引擎TTS 实时语音回声
- 麦克风输入 → ASR识别 → 识别完成的句子 → TTS合成播放
- 只播放完整句子（sentence_end = True）
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../语音'))

import pyaudio
import asyncio
import json
import uuid
import websockets
from threading import Thread, Lock
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
import dashscope
from dashscope.common.error import InvalidParameter

# 从火山引擎协议库导入
from protocols import EventType, MsgType, full_client_request, receive_message

# ==================== 配置 ====================
# 阿里云 DashScope API Key
DASHSCOPE_API_KEY = "sk-3bf1277c421648329ba41f0a4f7c9549"

# 火山引擎TTS配置
VOLC_APP_ID = "2634661217"
VOLC_ACCESS_TOKEN = "0im2q3lyhxDTTt5GXNtzmNSj2-I_Lb3b"
VOLC_VOICE_TYPE = "zh_male_naiqimengwa_mars_bigtts"  # 主音色（男声）
VOLC_FEMALE_VOICE = "ICL_zh_female_bingruoshaonv_tob"  # 女声音色（用于混合）
USE_MIXED_VOICE = True  # 是否使用混合音色
MALE_MIX_FACTOR = 0.45  # 男声混合比例（65%）
FEMALE_MIX_FACTOR = 0.55  # 女声混合比例（35%）
TTS_ENDPOINT = "wss://openspeech.bytedance.com/api/v3/tts/unidirectional/stream"

# 音频参数
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE_ASR = 16000  # ASR输入
RATE_TTS = 24000  # TTS输出

# 待播放的句子队列
sentence_list = []
sentence_lock = Lock()
tts_running = True
# =================================================

def get_resource_id(use_mixed: bool = False) -> str:
    """根据是否使用混合音色选择Resource ID"""
    # 根据火山引擎文档，混合音色应使用 volc.service_type.10029
    if use_mixed:
        return "volc.service_type.10029"
    # 单一音色时，根据音色类型判断
    if VOLC_VOICE_TYPE.startswith("S_"):
        return "volc.megatts.default"
    return "volc.service_type.10029"

async def tts_synthesize(text: str) -> bytes:
    """
    使用火山引擎TTS合成语音
    返回PCM音频数据
    """
    headers = {
        "X-Api-App-Key": VOLC_APP_ID,
        "X-Api-Access-Key": VOLC_ACCESS_TOKEN,
        "X-Api-Resource-Id": get_resource_id(use_mixed=USE_MIXED_VOICE),
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }

    try:
        websocket = await websockets.connect(
            TTS_ENDPOINT, 
            extra_headers=headers, 
            max_size=10 * 1024 * 1024
        )
        
        # 准备请求参数
        req_params = {
            "audio_params": {
                "format": "pcm",
                "sample_rate": RATE_TTS,
                "enable_timestamp": False,
            },
            "text": text,
            "additions": json.dumps({"disable_markdown_filter": False}),
        }
        
        # 根据配置选择使用单一音色还是混合音色
        if USE_MIXED_VOICE:
            # 混合音色：speaker 设置为 custom_mix_bigtts，添加 mix_speaker 参数
            req_params["speaker"] = "custom_mix_bigtts"
            req_params["mix_speaker"] = {
                "speakers": [
                    {
                        "source_speaker": VOLC_VOICE_TYPE,  # 男声
                        "mix_factor": MALE_MIX_FACTOR
                    },
                    {
                        "source_speaker": VOLC_FEMALE_VOICE,  # 女声
                        "mix_factor": FEMALE_MIX_FACTOR
                    }
                ]
            }
        else:
            # 单一音色：直接使用 speaker 字段
            req_params["speaker"] = VOLC_VOICE_TYPE
        
        request = {
            "user": {"uid": str(uuid.uuid4())},
            "req_params": req_params,
        }
        
        # 发送请求
        await full_client_request(websocket, json.dumps(request).encode())
        
        # 接收音频数据
        audio_data = bytearray()
        while True:
            msg = await receive_message(websocket)
            
            if msg.type == MsgType.FullServerResponse:
                if msg.event == EventType.SessionFinished:
                    break
            elif msg.type == MsgType.AudioOnlyServer:
                audio_data.extend(msg.payload)
            else:
                print(f"⚠️  TTS错误: {msg}")
                break
        
        await websocket.close()
        return bytes(audio_data)
        
    except Exception as e:
        print(f"❌ TTS合成失败: {e}")
        return b""

def play_audio(audio_data: bytes):
    """播放PCM音频数据"""
    if not audio_data:
        return
    
    p = pyaudio.PyAudio()
    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE_TTS,
            output=True,
            frames_per_buffer=1024
        )
        stream.write(audio_data)
        stream.stop_stream()
        stream.close()
    except Exception as e:
        print(f"❌ 播放失败: {e}")
    finally:
        p.terminate()

# ==================== TTS处理线程 ====================
def tts_worker():
    """TTS合成和播放线程"""
    global tts_running
    
    print("🔊 TTS播放器已启动")
    print("📋 等待ASR识别完整句子...\n")
    
    processed_count = 0  # 已处理的句子数量
    
    while tts_running:
        try:
            # 检查list中是否有新句子
            text = None
            with sentence_lock:
                if len(sentence_list) > processed_count:
                    text = sentence_list[processed_count]
                    processed_count += 1
            
            if text:
                print(f"\n🎯 [{processed_count}] 完整句子: {text}")
                print(f"🔄 正在合成语音...")
                
                # 异步合成
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_data = loop.run_until_complete(tts_synthesize(text))
                loop.close()
                
                if audio_data:
                    print(f"▶️  播放中 ({len(audio_data)} 字节)...")
                    play_audio(audio_data)
                    print(f"✅ 播放完成\n")
                else:
                    print(f"❌ TTS合成失败\n")
            else:
                # 没有新句子，等待一下
                import time
                time.sleep(0.1)
                        
        except Exception as e:
            if tts_running:
                print(f"❌ TTS处理错误: {e}")
    
    print("\n🔊 TTS播放器已关闭")
    print(f"📊 共播放 {processed_count} 句话")

# ==================== 阿里云ASR ====================
mic = None
stream = None
recognition_running = False

class Callback(RecognitionCallback):
    def on_open(self) -> None:
        global mic, stream, recognition_running
        print("✅ 阿里云ASR已启动")
        print("🎙️ 请开始说话（识别到完整句子会自动播放）\n")
        recognition_running = True
        
        mic = pyaudio.PyAudio()
        
        # 显式指定默认输入设备
        try:
            default_input = mic.get_default_input_device_info()
            stream = mic.open(
                format=FORMAT, 
                channels=CHANNELS, 
                rate=RATE_ASR, 
                input=True,
                input_device_index=default_input['index'],
                frames_per_buffer=3200
            )
            print(f"📱 使用输入设备: {default_input['name']}\n")
        except Exception as e:
            print(f"❌ 打开麦克风失败: {e}")
            raise

    def on_close(self) -> None:
        global mic, stream, tts_running, recognition_running
        print("\n✅ ASR识别结束")
        recognition_running = False
        tts_running = False  # 停止TTS线程
        try:
            if stream is not None:
                stream.stop_stream()
                stream.close()
        except Exception:
            pass
        finally:
            stream = None
        try:
            if mic is not None:
                mic.terminate()
        except Exception:
            pass
        finally:
            mic = None

    def on_event(self, result: RecognitionResult) -> None:
        sentence = result.get_sentence()
        
        if sentence:
            # 实时显示识别中的文本（sentence_end = False）
            if not sentence.get('sentence_end', False):
                text = sentence.get('text', '').strip()
                if text:
                    print(f"\r💬 识别中: {text}", end='', flush=True)
            
            # 只处理完整句子（sentence_end = True）
            elif sentence.get('sentence_end', True):
                text = sentence.get('text', '').strip()
                if text:
                    print(f"\r✅ 完整句子: {text}")
                    # 添加到队列
                    with sentence_lock:
                        sentence_list.append(text)
                        print(f"📝 已加入播放队列 (共{len(sentence_list)}句)\n")

# ==================== 主函数 ====================
def main():
    global tts_running, recognition_running
    
    # 设置阿里云API Key
    dashscope.api_key = DASHSCOPE_API_KEY
    
    print("=" * 60)
    print("🎙️  阿里云ASR → 火山引擎TTS 实时语音回声")
    print("=" * 60)
    print(f"ASR: 阿里云 Paraformer V2 (实时识别)")
    if USE_MIXED_VOICE:
        print(f"TTS: 混合音色 (更女性化)")
        print(f"  - 主音色: {VOLC_VOICE_TYPE} ({MALE_MIX_FACTOR*100:.0f}%)")
        print(f"  - 女声音色: {VOLC_FEMALE_VOICE} ({FEMALE_MIX_FACTOR*100:.0f}%)")
    else:
        print(f"TTS: 火山引擎 {VOLC_VOICE_TYPE}")
    print(f"模式: 只播放完整句子 (sentence_end = True)")
    print("=" * 60)
    print()
    
    # 屏蔽websockets的INFO日志
    import logging
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("protocols.protocols").setLevel(logging.WARNING)
    
    # 启动TTS处理线程
    tts_thread = Thread(target=tts_worker, daemon=True)
    tts_thread.start()
    
    # 启动ASR识别
    recognition = Recognition(
        model="paraformer-realtime-v2",
        format="pcm",
        sample_rate=RATE_ASR,
        language_hints=["zh"],
        disfluency_removal_enabled=True,  # 去掉"嗯"、"啊"
        callback=Callback()
    )
    
    recognition.start()
    
    # 等待 stream 初始化
    import time
    timeout = 5  # 等待最多5秒
    start_time = time.time()
    while stream is None and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if stream is None:
        print("❌ 无法初始化音频流")
        recognition.stop()
        tts_running = False
        return
    
    try:
        # 持续发送音频
        while recognition_running and stream and tts_running:
            try:
                data = stream.read(3200, exception_on_overflow=False)
                recognition.send_audio_frame(data)
            except InvalidParameter:
                # 识别已停止，退出发送循环
                break
            except Exception as e:
                if recognition_running:
                    print(f"⚠️  发送音频帧错误: {e}")
                break
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断")
    finally:
        try:
            if recognition_running:
                recognition.stop()
        except (InvalidParameter, Exception):
            # 已停止或出错则忽略
            pass
        tts_running = False
        # 等待TTS线程处理完
        print("\n⏳ 等待播放队列清空...")
        tts_thread.join(timeout=5)
        print("\n👋 程序退出")

# ==================== 启动 ====================
if __name__ == "__main__":
    main()

