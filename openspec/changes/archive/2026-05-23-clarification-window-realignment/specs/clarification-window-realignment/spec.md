## ADDED Requirements

### Requirement: Playout Decay Isolation
The system SHALL block microphone ingestion when transitioning to a clarification turn until both `config.SPEAKER_ACTIVE` and `config.TTS_PROCESSING` have dropped to `False` for a contiguous room-decay window of at least 300ms.

#### Scenario: Audio Playout Cooldown Active
- **WHEN** speaking finishes and `config.WAITING_FOR_CLARIFICATION` is True
- **THEN** the system SHALL enter `AppState.ROOM_COOLDOWN_FOLLOW_UP`, flush lingering leak frames, and sleep for 300ms before starting to listen.

### Requirement: Dynamic Dual-Phase Follow-Up Gate
The system SHALL enforce a rolling 5.0-second maximum follow-up window tracker once proactive listening begins.

#### Scenario: Follow-Up Window Timeout
- **WHEN** 5.0 seconds elapse in `AppState.FOLLOW_UP_LISTENING` without any human speech signals detected
- **THEN** the system SHALL transition back to `AppState.IDLE` and reset the visualizer state.

### Requirement: Instant Cut-Off Dispatch
If speech starts within the follow-up window, the system SHALL track trailing quiet frames and instantly dispatch the recording buffer to Whisper STT once a 600ms (20 frames) silence threshold is reached.

#### Scenario: User Responds and Finishes Speaking
- **WHEN** speech is detected and then followed by 20 consecutive quiet frames
- **THEN** the system SHALL transition `config.CURRENT_STATE` to `AppState.THINKING` and put the recorded audio buffer into `config.STT_STREAM_QUEUE`.
