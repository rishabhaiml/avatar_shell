## Context

B.H.A.I. is designed as a local voice assistant. On Linux, it runs a native translucent window overlay powered by PyGObject and WebKitGTK, and captures/plays audio using `webrtcvad` and `pyaudio`. However, the C-extensions for PyGObject, PortAudio, and WebRTC VAD do not have precompiled wheels for Windows, causing build/installation failures when using `uv sync` or `pip` on Windows. We must provide a seamless, compile-free fallback path for Windows systems.

## Goals / Non-Goals

**Goals:**
- Eliminate all compilation barriers on Windows, allowing `uv sync` to complete instantly with zero compile failures.
- Provide a robust Web Browser fallback rendering scene that automatically starts local servers and launches the user's default browser to load the Three.js visualizer.
- Implement pure-Python fallbacks for both Voice Activity Detection (VAD) and hardware audio input/output streaming.

**Non-Goals:**
- Porting GTK 4 or WebKitGTK native layers to Windows.
- Replacing Whisper, llama-cpp, or openWakeWord (which already support Windows natively through standard precompiled ONNX/wheel binaries).

## Decisions

### Decision 1: Web Browser GUI Fallback
We will conditionally import `gi`, `WebKit`, and `Gtk`. If they fail to load (default Windows behavior), B.H.A.I. will execute in "Browser Mode." It will serve the static UI at `http://127.0.0.1:8000` and automatically open the default system web browser using the Python standard library's `webbrowser.open()` module.
- *Alternative Considered*: Porting PyGObject via MSYS2. Rejected due to the extreme setup complexity for end-users.

### Decision 2: Pure-Python Energy VAD Fallback
If the C-compiled `webrtcvad` is not present, the system will use a dynamic RMS energy-threshold VAD. By calculating the frame's RMS energy `float(np.sqrt(np.mean(np.square(frame))))` and comparing it to a dynamic noise-floor average (maintained via `config.ambient_noise_rms`), we can identify speech starts and stops with zero native library dependencies.
- *Alternative Considered*: Silero VAD. Rejected to maintain ultra-low CPU overhead on resource-constrained setups.

### Decision 3: Sounddevice Audio Fallback
When `pyaudio` fails to import, the system will dynamically route microphone capture and speaker playout through a standard `sounddevice` interface. `sounddevice` and `soundfile` bundle precompiled PortAudio binaries for all major platforms (including Windows), ensuring compile-free execution.
- *Alternative Considered*: PyAudio binary wheels. Rejected because prebuilt wheels are not consistently available for newer Python versions (3.12, 3.13) on Windows.

## Risks / Trade-offs

- **[Risk] Browser Window Focus**: Opening a web browser tab is not as tightly integrated as a native overlay window. 
  - *Mitigation*: The `webbrowser.open()` invocation automatically brings the browser tab to the front on Windows, presenting a beautiful full-screen visualizer experience.
- **[Risk] Energy-Based VAD Sensitivity**: Simple energy VADs are more sensitive to sudden background noises compared to WebRTC VAD.
  - *Mitigation*: Leverage B.H.A.I.'s existing robust `config.NOISE_WINDOW` and adaptive SNR registers to continuously adapt the threshold to ambient environment sounds.
