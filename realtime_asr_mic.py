#!/usr/bin/env python3
"""
火山引擎 ASR 实时麦克风识别（基于 aiohttp，完全遵循官方协议）
- 使用 Gzip 压缩 + Sequence
- 逐字流式输出（监听 result.text）
- 无需停顿，边说边出字
"""
import asyncio
import aiohttp
import pyaudio
import json
import struct
import gzip
import uuid

# ================== 配置 ==================
APP_ID = "8902092095"
ACCESS_TOKEN = "b2VWfrJpqMzNNlGHAyMsQUz_x_2yn3ZX"
WS_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK_SAMPLES = 3200  # 200ms

# ================== 协议常量 ==================
class MessageType:
    FULL_CLIENT_REQ = 0b0001
    AUDIO_ONLY_REQ = 0b0010
    FULL_SERVER_RESP = 0b1001

def build_header(msg_type, flags=0b0001, serial=0b0001, comp=0b0001):
    """构建 4 字节 Header（Gzip + JSON）"""
    header = bytearray()
    header.append((0b0001 << 4) | 0b0001)  # version=1, size=1
    header.append((msg_type << 4) | flags)
    header.append((serial << 4) | comp)
    header.append(0x00)  # reserved
    return bytes(header)

def gzip_compress(data: bytes) -> bytes:
    return gzip.compress(data)

def build_full_client_request(seq: int):
    config = {
        "user": {"uid": "mic_user"},
        "audio": {
            "format": "wav",
            "codec": "raw",
            "rate": RATE,
            "bits": 16,
            "channel": CHANNELS
        },
        "request": {
            "model_name": "bigmodel",
            "enable_punc": True,
            "enable_itn": True
        }
    }
    payload = gzip_compress(json.dumps(config).encode('utf-8'))
    buf = bytearray()
    buf.extend(build_header(MessageType.FULL_CLIENT_REQ))
    buf.extend(struct.pack('>i', seq))      # Sequence
    buf.extend(struct.pack('>I', len(payload)))  # Payload size
    buf.extend(payload)
    return bytes(buf)

def build_audio_packet(seq: int, audio_ bytes, is_last: bool = False):
    flags = 0b0011 if is_last else 0b0001  # NEG_WITH_SEQUENCE or POS_SEQUENCE
    header = build_header(MessageType.AUDIO_ONLY_REQ, flags=flags, serial=0b0000, comp=0b0001)
    compressed = gzip_compress(audio_data)
    buf = bytearray()
    buf.extend(header)
    buf.extend(struct.pack('>i', -seq if is_last else seq))
    buf.extend(struct.pack('>I', len(compressed)))
    buf.extend(compressed)
    return bytes(buf)

def parse_response(msg: bytes):
    if len(msg) < 4:
        return None
    header_size = msg[0] & 0x0F
    flags = msg[1] & 0x0F
    comp = msg[2] & 0x0F
    payload = msg[header_size * 4:]
    
    # 跳过 Sequence (4B)
    if flags & 0x01:
        payload = payload[4:]
    
    # 跳过 Payload Size (4B)
    if len(payload) < 4:
        return None
    payload_size = struct.unpack('>I', payload[:4])[0]
    payload = payload[4:4 + payload_size]
    
    if comp == 0b0001:  # Gzip
        payload = gzip.decompress(payload)
    
    return json.loads(payload.decode('utf-8'))

# ================== 主逻辑 ==================
async def main():
    print("🔌 正在连接火山引擎 ASR (aiohttp + Gzip + Sequence)...")
    
    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK_SAMPLES
    )

    headers = {
        "X-Api-App-Key": APP_ID,
        "X-Api-Access-Key": ACCESS_TOKEN,
        "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
        "X-Api-Connect-Id": str(uuid.uuid4())
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(WS_URL, headers=headers) as ws:
                print("✅ WebSocket 连接成功")
                
                # 发送初始化
                await ws.send_bytes(build_full_client_request(1))
                
                seq = 2
                print("🎙️ 开始流式识别（边说边出字）")

                async def send_audio():
                    nonlocal seq
                    while True:
                        audio_data = stream.read(CHUNK_SAMPLES, exception_on_overflow=False)
                        await ws.send_bytes(build_audio_packet(seq, audio_data))
                        seq += 1
                        await asyncio.sleep(0.001)

                async def recv_results():
                    while True:
                        msg = await ws.receive()
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            try:
                                resp = parse_response(msg.data)
                                if resp and 'result' in resp:
                                    text = resp['result'].get('text', '').strip()
                                    if text:
                                        print(f"\r🔤 {text}", end='', flush=True)
                            except Exception as e:
                                print(f"\n❌ 解析错误: {e}")
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break

                await asyncio.gather(send_audio(), recv_results())

        except Exception as e:
            print(f"\n❌ 连接错误: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

if __name__ == "__main__":
    asyncio.run(main())