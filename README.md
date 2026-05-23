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

# Sync all virtualenv dependencies automatically (Linux & Windows Out-Of-The-Box!)
uv sync
```

> [!NOTE]
> **Windows Compatibility**: The project is fully compatible with Windows! C-extension dependencies like `webrtcvad`, `pyaudio`, and `pygobject` are ignored on Windows via PEP 508 markers. B.H.A.I. will automatically fallback to "Web Browser Mode," opening your default system web browser to render the 3D visualizer. No complex compilers or setup are required!

### 2. Download & Configure Large Assets & Models (Super Easy!)

To keep the repository lightweight, large model weights and avatar assets are excluded from Git. We provide a **completely automated, cross-platform setup script** that downloads and extracts all GGUF models, VRM avatars, and offline Kokoro speech weights in one click.

Simply execute:

```bash
uv run setup_models.py
```

*This script works flawlessly on both **Windows** and **Linux** without requiring external utilities like `wget`, `curl`, `tar`, or `unzip` since it uses Python's standard library.*

---

#### 🛠️ Manual Alternative (If you prefer downloading via your browser)

If you prefer to download files manually, place them in the correct directories:

1. **Avatar VRM & LLM Brain Model**:
   * Go to the **[GitHub Release Page](https://github.com/rishabhaiml/avatar_shell/releases/tag/model)**.
   * Download **`model.vrm`** and place it in the `www/` folder:
     * **Target Path:** `www/model.vrm`
   * Download **`model.gguf`** and place it in the project root directory:
     * **Target Path:** `./model.gguf`

2. **Offline Kokoro TTS Weights**:
   * Download the C++ ready offline Kokoro bundle: **[Download kokoro-v1.0.tar.bz2](https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-v1.0.tar.bz2)**
   * Extract the bundle inside the `weights/` folder.
   * **Target Directory Structure:**
     * `weights/kokoro-v1.0/model.onnx`
     * `weights/kokoro-v1.0/voices.bin`
     * `weights/kokoro-v1.0/tokens.txt`
     * `weights/kokoro-v1.0/espeak-ng-data/`
     * `weights/kokoro-v1.0/dict/`
     * `weights/kokoro-v1.0/lexicon-us-en.txt`

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
