# dynamic-cadence-backoff Specification

## Purpose
TBD - created by archiving change dynamic-cadence-backoff. Update Purpose after archive.
## Requirements
### Requirement: Conjunction Pause Interrogation
The system SHALL monitor consecutive silence frame counts during `FOLLOW_UP_LISTENING` turns. The instant the silence counter transitions to exactly 1 frame (`config.consecutive_quiet == 1`), the orchestrator MUST spawn a non-blocking background thread task to run a sub-second, greedy search Whisper STT inference on the currently accumulated audio buffer bytes, checking for active speech cadence patterns.

#### Scenario: Pause triggers non-blocking background partial transcription check
- **WHEN** the user is speaking in the wake-word-free follow-up phase and pauses so that `config.consecutive_quiet` becomes 1
- **THEN** B.H.A.I. spawns a background thread to run Whisper STT on the trailing audio chunks in parallel with state machine polling.

### Requirement: Adaptive Silence Threshold Gating
The voice endpointing loop SHALL dynamically adjust the silence cut-off limit variable `config.DYNAMIC_SILENCE_LIMIT`. If the partial transcript obtained during a pause finishes on a loose coordinating or subordinating conjunction (including `"because"`, `"but"`, `"so"`, `"and"`, `"or"`, `"if"`, `"then"`, `"like"`), the system MUST scale the threshold from its default of 20 frames (600ms) to 40 frames (1200ms) to allow the user to complete their thought. If the sentence terminates with standard punctuation or a noun/verb, the limit MUST remain at 20 frames for snappiness.

#### Scenario: Trailing conjunction doubles the silence limit to 1200ms
- **WHEN** the partial transcript returns with a trailing word `"because"`
- **THEN** the system scales `config.DYNAMIC_SILENCE_LIMIT` to 40, keeping the microphone hot for up to 1.2 seconds of pause.

