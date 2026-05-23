# B.H.A.I. Avatar Shell 🎤🤖

B.H.A.I. (Behavioral Humanlike AI) is a highly interactive, voice-driven local AI assistant featuring a stunning, real-time animated 3D avatar. It bridges local language models (LLMs), fast voice activity detection (VAD), off-line Text-to-Speech (TTS) via Kokoro ONNX, and WebSockets to deliver a full-duplex conversational experience (Jarvis-Symmetry).

---

## 🏛️ Project Architecture

* **`main.py`**: The central orchestrator bootstrapping GTK, WebKit, websockets, and background audio/cognitive thread systems.
* **`audio/`**: Hardware audio capture, playback buffers, and noise-purified WebRTC VAD + openWakeWord + fast Whisper STT.
* **`brain/`**: The local LLM inference driver (via `llama-cpp-python`) and off-line Kokoro speech synthesizer.
* **`ui/`**: Translucent GTK 4 + WebKit window layers supporting Wayland Overlay positioning.
* **`www/`**: 3D VRM avatar scene using Three.js and `@pixiv/three-vrm` with volume-driven lip sync.
* **`memory/`**: Vectorless cognitive stopword relevance database engine tracking long-term developer graphs.

---

## ⚡ Quick Start (Setup & Installation)

The project leverages modern Python packaging via `uv`. You can clone, synchronize dependencies, download the assets, and boot B.H.A.I. in a few minutes.

### 1. Clone the Repository & Sync Dependencies

Make sure you have [uv](https://github.com/astral-sh/uv) installed, then execute:

```bash
git clone https://github.com/rishabhaiml/avatar_shell.git
cd avatar_shell

# Sync all virtualenv dependencies automatically
uv sync
```

### 2. Download Large Assets & Models

To keep the repository lightweight, large model weights and avatar assets are excluded from Git. Download them and place them in their respective paths:

#### A. Avatar VRM & Brain GGUF Models
We have hosted pre-aligned models on our release page:
👉 **[Download Models from Release Page](https://github.com/rishabhaiml/avatar_shell/releases/tag/model)**

1. Download **`model.vrm`** and place it in the `www/` folder:
   * **Target Path:** `www/model.vrm` (Double cache-busters are active to refresh changes instantly!)
2. Download the GGUF LLM model (e.g. **`model.gguf`**) and place it in the project root directory:
   * **Target Path:** `./model.gguf`

#### B. Off-line Kokoro TTS Weights
B.H.A.I. utilizes Kokoro v1.0 running natively under `sherpa-onnx` for high-fidelity speech synthesis. 

Run the following commands to create the target directory, download, and unpack the compiled weights:

```bash
# Create weights directory
mkdir -p weights

# Download the C++ ready offline Kokoro bundle
wget https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-v1.0.tar.bz2

# Extract and clean up the archive
tar xf kokoro-v1.0.tar.bz2 -C weights/
rm kokoro-v1.0.tar.bz2
```
* **Verify Path:** Ensure you have `./weights/kokoro-v1.0/model.onnx` and `./weights/kokoro-v1.0/voices.bin` in place.

---

## 🎮 Running the Avatar

Once the models and weights are configured in the directories, start the assistant by launching the main script:

```bash
uv run main.py
```

### Features at Runtime:
* **Attentive Listening & Lip Sync**: B.H.A.I. features responsive, volume-driven smooth facial lip-sync with random eye blinks.
* **Premium Voice Configuration**: Equipped with the highly expressive American Male voice **Michael** (`am_michael` - index `16` in `voices.bin`).
* **Double-Layer Cache Bypassing**: Both WebKit and Three.js are configured with dynamic timestamp query parameters, meaning any updates to your `./www/model.vrm` file are picked up instantly without restarting your browser or purging caches.
