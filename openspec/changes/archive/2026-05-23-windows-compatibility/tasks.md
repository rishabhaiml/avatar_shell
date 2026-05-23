## 1. PyGObject GUI Fallback & Browser Mode

- [x] 1.1 Wrap PyGObject, Gtk, and WebKit imports in `main.py` and `ui/window.py` inside clean `try...except ImportError` blocks
- [x] 1.2 Add platform check and register active status for "Browser Mode" in `config.py`
- [x] 1.3 Add automatic web browser trigger inside `main.py` using `webbrowser.open()` to launch the visualizer when WebKit is absent
- [x] 1.4 Gracefully bypass GTK native window initialization when native graphic libraries are not loaded

## 2. Compile-Free Audio & VAD fallbacks

- [x] 2.1 Wrap `webrtcvad` imports and implement a dynamic, pure-Python RMS-based VAD algorithm in `audio/vad.py` to trigger speech state transitions without native bindings
- [x] 2.2 Wrap `pyaudio` imports in `audio/pipeline.py` and `main.py` inside clean `try...except` statements
- [x] 2.3 Implement robust fallback capture loop inside `audio/pipeline.py` using `sounddevice.InputStream`
- [x] 2.4 Implement robust fallback playback loop inside `audio/pipeline.py` using `sounddevice.OutputStream`

## 3. Dependency Tuning & Verification

- [x] 3.1 Optimize platform-specific dependencies inside `pyproject.toml` so that `uv sync` installs successfully on Windows out of the box
- [x] 3.2 Execute syntax and compilation checks to verify all conditional execution blocks compile cleanly
