# 实时变声 - ASR & TTS 模块

阿里云 ASR + 火山引擎 TTS 实时语音处理系统

## 📦 依赖安装

### 1. 安装 Python 包

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install pyaudio>=0.2.11
pip install dashscope>=1.14.0
pip install websockets==10.4
```

### 2. 系统依赖（Linux）

如果安装 `pyaudio` 遇到问题，需要先安装系统依赖：

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install portaudio19-dev python3-dev
```

**Fedora/CentOS:**
```bash
sudo dnf install portaudio-devel python3-devel
```

## 🔑 配置 API 密钥

### 阿里云 DashScope (ASR)

设置环境变量：
```bash
export DASHSCOPE_API_KEY="your-dashscope-api-key"
```

或在代码中设置：
```python
import dashscope
dashscope.api_key = "your-dashscope-api-key"
```

### 火山引擎 (TTS)

在代码中已配置（`doubao_tts.py` 和 `asr_to_tts.py`）：
- APP_ID: `2634661217`
- ACCESS_TOKEN: `0im2q3lyhxDTTt5GXNtzmNSj2-I_Lb3b`

## 🚀 使用方法

### 1. 阿里云 ASR（单独识别）

```bash
python3 aliyun_asr.py
```

功能：麦克风实时语音识别，输出识别结果

### 2. 火山引擎 TTS（交互式合成）

```bash
python3 doubao_tts.py
```

功能：输入文本 → 语音合成 → 播放

### 3. ASR → TTS 实时回声 ⭐

```bash
python3 asr_to_tts.py
```

功能：
- 麦克风输入 → ASR 识别 → TTS 合成 → 扬声器播放
- 只播放完整句子（`sentence_end = True`）
- 实时显示识别中的文本

### 4. 阿里云语音翻译示例

```bash
python3 official_demo.py
```

功能：实时语音识别 + 中英翻译

## 📁 文件说明

```
实时变声/
├── aliyun_asr.py           # 阿里云ASR实时识别
├── doubao_tts.py           # 火山引擎TTS交互式合成
├── asr_to_tts.py           # ASR→TTS完整流程 ⭐
├── official_demo.py        # 阿里云语音翻译示例
├── protocols/              # 火山引擎协议库
│   ├── __init__.py
│   └── protocols.py
├── requirements.txt        # Python依赖列表
└── README.md              # 本文件
```

## 🔧 常见问题

### ALSA 警告

运行时可能出现大量 ALSA 警告：
```
ALSA lib pcm_dsnoop.c:601:(snd_pcm_dsnoop_open) unable to open slave
```

**解决方案**：这些警告不影响功能，可以忽略。

### PyAudio 安装失败

如果 `pip install pyaudio` 失败：

1. 确保已安装系统依赖（见上文）
2. 尝试使用预编译版本：
   ```bash
   pip install pipwin
   pipwin install pyaudio
   ```

### 麦克风无声

如果 ASR 识别不出来：
1. 检查麦克风音量（调到最大）
2. 检查系统音频设备：
   ```bash
   arecord -l  # 列出录音设备
   ```

## 🎯 技术栈

- **ASR**: 阿里云 DashScope (Paraformer V2)
- **TTS**: 火山引擎 (豆包 TTS)
- **音频**: PyAudio
- **通信**: WebSockets
- **协议**: 火山引擎自定义二进制协议

## 📝 License

MIT License

