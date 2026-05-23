## Why

Currently, during wake-word-free follow-up listening turns (`FOLLOW_UP_LISTENING`), B.H.A.I. enforces a rigid 20-frame (~600ms) silence cutoff threshold. This routinely interrupts users who pause mid-thought to assemble complex clauses, especially when ending on coordinating or subordinating conjunctions (e.g. "because...", "but..."). Implementing a dynamic silence cadence backoff will dramatically improve conversation fluidity by giving the user a longer window to complete their thoughts when they pause on conjunctions.

## What Changes

- **Partial Text Suffix Sniffing**: The system will trigger a fast, non-blocking background Whisper STT check when a pause begins (transitioning to `consecutive_quiet == 1`).
- **Dynamic Threshold Scaling**: The silence limit will dynamically scale from 20 frames (600ms) to 40 frames (1200ms) if the trailing sentence block ends with a conjunction ("because", "but", "so", "and", "or", "if", "then", "like"), giving the user breathing room.
- **Dynamic Limit Counter**: Refactor the rigid frame limit check to use `config.DYNAMIC_SILENCE_LIMIT`, which gets re-initialized at 20 frames on every voice turn and scales to 40 on a detected conjunction pause.

## Capabilities

### New Capabilities
- `dynamic-cadence-backoff`: Covers partial audio streaming sniffing, sub-second Whisper transcription tails, and adaptive threshold cadence scaling rules.

### Modified Capabilities
<!-- None. Behavior is being introduced as a new subsystem capability to adapt active voice turns. -->

## Impact

- **Affected Systems**: `main.py` (process_audio_queue, FOLLOW_UP_LISTENING case), `config.py` (status registers).
- **APIs & Dependencies**: Whisper STT Model (faster-whisper inference), zero-crossing VAD accumulators.
