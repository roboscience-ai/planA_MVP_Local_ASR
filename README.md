# 实时语音识别方案集合

本仓库包含多个本地实时语音识别的实现方案。

## 📁 文件说明

### 1. `realtime_asr_mic.py` - 火山引擎 ASR
使用火山引擎大模型进行实时语音识别。

**特性**：
- ✅ 双向流式识别，边说边出字
- ✅ 使用 bigmodel 大模型
- ✅ 支持标点符号和数字转写
- ✅ WebSocket v3 协议

**依赖**：
```bash
pip install websockets==10.4 pyaudio
```

**配置**：
```python
APP_ID = "您的APP_ID"
ACCESS_TOKEN = "您的ACCESS_TOKEN"
```

**使用**：
```bash
python3 realtime_asr_mic.py
```

---

### 2. `aliyun_asr.py` - 阿里云 Paraformer V2
专注于中文识别，使用阿里云通义千问 Paraformer V2 模型。

**特性**：
- ✅ 针对中文优化
- ✅ 自动过滤语气词（"嗯"、"啊"等）
- ✅ 实时流式识别
- ✅ 简洁的 API

**依赖**：
```bash
pip install dashscope pyaudio
```

**配置**：
```bash
export DASHSCOPE_API_KEY="您的API_KEY"
```

**使用**：
```bash
python3 aliyun_asr.py
```

---

### 3. `official_demo.py` - 阿里云翻译识别
官方示例，同时支持语音识别和实时翻译。

**特性**：
- ✅ 实时语音识别
- ✅ 实时翻译（中译英）
- ✅ Gummy 模型

---

## 📊 方案对比

| 特性 | 火山引擎 | 阿里云 Paraformer | 阿里云翻译 |
|------|---------|-------------------|-----------|
| 中文识别 | ✅ | ✅ 优化 | ✅ |
| 标点符号 | ✅ | ✅ | ✅ |
| 语气词过滤 | ❌ | ✅ | ✅ |
| 实时翻译 | ❌ | ❌ | ✅ |

## �� 技术参数

- **音频格式**：PCM 16-bit
- **采样率**：16kHz
- **声道**：单声道
- **音频分包**：3200 样本（200ms）

## 📄 License

MIT
