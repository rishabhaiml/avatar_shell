## Context

To resolve the physical hardware playout tail leakage where the speaker is still audibly outputting Kokoro speech while the microphone has already opened, B.H.A.I. must introduce a dedicated audio playout drain gate. This proposal isolates playout decay, shields the microphone from self-barge-in during follow-up turns, and implements a responsive 5.0-second dynamic listening state.

## Goals / Non-Goals

**Goals:**
- Implement `AppState.ROOM_COOLDOWN_FOLLOW_UP` state in `config.py` and `main.py` to sleep for 300ms and completely purge microphone queue leakage during audio playout decay.
- Implement a thread-safe 5.0s maximum capture window under `AppState.FOLLOW_UP_LISTENING`.
- Implement dynamic speech detection (via RMS/VAD) that tracks trailing quiet frames and instantly dispatches the frame buffer to Whisper STT when a 600ms (20 consecutive frames) silence envelope is met.
- Provide graceful timeouts back to `AppState.IDLE` if no voice is registered within the 5.0-second window.

**Non-Goals:**
- Changing standard non-clarification turn pipelines.
- Replacing PyAudio sound card backend architectures.

## Decisions

### 1. Dedicated Acoustic Cooldown State
- **Choice**: Introduce a separate `AppState.ROOM_COOLDOWN_FOLLOW_UP` step.
- **Rationale**: Keeps the state machine highly cohesive and guarantees that we wait for physical sound waves in the room to decay fully, constantly purging the audio frame queue down to zero before opening the mic stream.
- **Alternative**: Multi-threading synchronization hooks (fragile and prone to lockups due to audio card hardware buffers).

### 2. Trailing Silence Slicing
- **Choice**: Quiet envelope VAD checks (20 frames / 600ms silence threshold).
- **Rationale**: Responds instantly as soon as the user finishes speaking their follow-up, keeping voice capture fluid and fast.

## Risks / Trade-offs

- **[Risk]** Room Echo Leakage → **[Mitigation]** The 300ms sleep includes a continuous non-blocking drain pass of `config.AUDIO_FRAME_QUEUE` to throw away any speaker output recorded during playout decay.
