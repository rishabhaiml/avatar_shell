# Avatar Shell

Avatar Shell is a highly interactive, voice-driven AI assistant featuring a 3D visual avatar. It bridges local language models (LLMs), fast voice activity detection (VAD), text-to-speech (TTS) via Kokoro/Piper, and WebRTC elements to present a comprehensive, interlocked audiovisual experience.

## 🧠 Project Architecture

* **`audio/`**: Handles the Voice Activity Detection (VAD) and audio processing pipeline (using `webrtcvad`, `faster-whisper`, `openwakeword`).
* **`brain/`**: The core logic driver, connecting user input to generating responses via the underlying LLM (powered by `llama-cpp-python`) and normalizing conversation flows.
* **`memory/`**: Engine and systems to maintain short and long-term conversation history context.
* **`ui/` & `www/`**: A combined front-end utilizing a 3D VRM model rendered in a web environment, communicating over WebSockets with the Python backend.

---

## 🚀 Installation & Setup Guide

### 1. Python Environment Setup
We recommend using standard Python virtual environments or `uv` for managing dependencies. The project requires Python 3.12+.

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies via pip
pip install -r requirements.txt
# OR if using `uv` with pyproject.toml
uv pip install -e .
```

### 2. Large Assets & Models Download
To keep this repository lightweight, large artifacts like AI models, binaries, and weights have been ignored in version control (`.gitignore`). Before you run the project, please download and organize the following components:

#### A. LLM Model (Brain)
Download your preferred `.gguf` model (e.g., Llama 3, Mistral, etc.) from [HuggingFace GGUF Models](https://huggingface.co/models?search=gguf) and place it directly in the project root folder.
* **Path:** `./model.gguf`

#### B. Kokoro TTS Weights
The engine leverages Kokoro for ultra-realistic Text-to-Speech.
* **Download:** Grab the `v1.0` weights and lexicon mappings from the [Kokoro-82M HuggingFace Repository](https://huggingface.co/hexgrad/Kokoro-82M).
* **Path:** Place the contents (like `lexicon-us-en.txt`, etc.) in `./weights/kokoro-v1.0/`

#### C. Piper TTS Binaries
We use Piper for localized, speedy fallback/alternate TTS processing. 
* **Download:** Get the built binaries for your specific OS (Linux/Windows/macOS) from [Rhasspy Piper Releases](https://github.com/rhasspy/piper/releases).
* **Path:** Extract the binaries into the `./piper/` directory (you should see items like `piper`, `piper_phonemize`, `libonnxruntime.so.*`).

#### D. Ensure Your 3D Avatar (VRM File)
To visualize the agent, provide a standard `.vrm` file. You can download starter avatars from [VRoid Hub](https://hub.vroid.com/en/).
* **Path:** `./www/model.vrm`

---

## 🎮 Running the Project

Once all dependencies are installed and the models/assets are situated in their respective directories, simply launch the backend application!

```bash
uv run main.py
# OR
python main.py
```

The system will initialize the voice pipelines, boot up the local LLM, and launch the localized UI rendering the interactions. Enjoy your new Avatar assistant!
