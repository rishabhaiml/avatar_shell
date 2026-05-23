## Why

Currently, B.H.A.I. is highly optimized for Linux, relying on PyGObject (`gi`), WebKitGTK, and system-level C-compiled dependencies like `webrtcvad` and `pyaudio`. On Windows, installing and compiling these C-based extensions requires complex compiler environments (MSYS2, Visual Studio build tools, PortAudio headers), creating a major adoption barrier for Windows users who want to run B.H.A.I. natively with simple commands like `uv sync`.

## What Changes

We will introduce a robust, compile-free Windows compatibility mode:
- **PyGObject/WebKit Fallback**: When PyGObject/WebKit is missing or running under Windows, the system will automatically transition from native GTK window rendering to "Browser Mode." It will serve the interactive 3D visualizer at `http://127.0.0.1:8000/index.html` and automatically launch it in the user's default web browser.
* **Compile-Free VAD Fallback**: Introduce a pure-Python amplitude-based (RMS) VAD tracker that executes when the C-compiled `webrtcvad` module is not installed or fails to load.
* **Compile-Free Audio I/O Fallback**: Incorporate a `sounddevice`/`soundfile` recording and playback fallback interface that activates when `pyaudio` fails to compile or load.
* **Cross-Platform Dependencies**: Update package metadata to list platform-specific dependencies correctly so that Windows users get a fully functioning, compile-free environment upon running `uv sync`.

## Capabilities

### New Capabilities
- `windows-compatibility`: Enables B.H.A.I. to boot and execute natively on Windows without requiring PyGObject, compiled VAD binaries, or complex build tools.

### Modified Capabilities
*None.*

## Impact

* **`main.py`**: Conditionally import `gi`, `WebKit`, and `Gtk` modules. Gracefully fallback to opening the static webpage using the standard `webbrowser` library when in Windows/Browser mode.
* **`audio/pipeline.py`**: Conditionally import `pyaudio` and load a robust `sounddevice`-based fallback stream when PyAudio is absent.
* **`audio/vad.py` & `main.py`**: Gracefully handle absent `webrtcvad` bindings by falling back to a pure-Python energy-based VAD.
* **`pyproject.toml`**: Optimize platform dependency groups so `uv sync` installs successfully on both Windows and Linux out of the box.
