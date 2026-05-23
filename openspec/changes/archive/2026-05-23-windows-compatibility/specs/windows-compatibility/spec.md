## ADDED Requirements

### Requirement: Fallback to Browser Mode
The system SHALL gracefully detect if the PyGObject (`gi`), GTK 4, or WebKitGTK graphic rendering engine libraries are absent or fail to load, and automatically fallback to Web Browser Mode.

#### Scenario: Missing native GUI libraries on boot
- **WHEN** B.H.A.I. launches and PyGObject libraries fail to import
- **THEN** the system SHALL proceed with initialization and set the rendering mode to Web Browser Mode

### Requirement: Automatic Browser Invocation
The system SHALL start a local HTTP server on port 8000 to host `./www/` static assets, launch a WebSocket relay server on port 8765, and automatically open the default system web browser to display the 3D avatar visualizer interface.

#### Scenario: Running visualizer in fallback browser mode
- **WHEN** B.H.A.I. boots in Web Browser Mode
- **THEN** the system SHALL start the static web server and WebSocket servers, and invoke `webbrowser.open()` to load the visualizer with a dynamic cache-buster parameter

### Requirement: Compile-Free VAD Fallback
The system SHALL utilize a robust, pure-Python energy-based (RMS) Voice Activity Detection algorithm when the compiled `webrtcvad` library is not present in the execution environment.

#### Scenario: Active speech tracking without C-compiled VAD
- **WHEN** B.H.A.I. records microphone frames and `webrtcvad` is not installed
- **THEN** the system SHALL calculate the Root Mean Square (RMS) energy delta of incoming audio and trigger speech/silence transitions algorithmically

### Requirement: Compile-Free Audio stream Fallback
The system SHALL switch to a pure-Python `sounddevice` and `soundfile` driver layer for hardware capture and playback when the C-compiled `pyaudio` library is not present in the execution environment.

#### Scenario: Hardware recording and playout without PyAudio
- **WHEN** B.H.A.I. accesses audio hardware and `pyaudio` is not installed
- **THEN** the system SHALL instantiate a `sounddevice.InputStream` for microphone capture and a `sounddevice.OutputStream` for speech playback
