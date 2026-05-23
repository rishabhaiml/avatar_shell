## Why

Resolve the conversational loop issue where B.H.A.I. cuts off follow-up inputs or suffers self-barge-in cascades due to audio playout tail leakage. The speaker hardware plays out Kokoro audio blocks for another 400ms–800ms after synthesis completes, which the microphone catches as human speech, triggering false barge-ins and aborting the turn. 

## What Changes

- **Acoustic Playout Cooldown**: Implement `AppState.ROOM_COOLDOWN_FOLLOW_UP` to wait for a hard 300ms room acoustics decay period, flushing lingering audio leak frames from the mic queue before listening.
- **Precision 5-Second Conversational Gate**: Introduce a dynamic dual-phase `AppState.FOLLOW_UP_LISTENING` window that keeps the microphone active for exactly 5.0 seconds.
- **Dynamic Utterance Truncation**: Track quiet envelopes in the proactive listening loop. If speech is detected, the moment a 600ms quiet threshold (20 frames) is met, instantly compile and dispatch the audio frame buffer to Whisper STT.

## Capabilities

### New Capabilities
- `clarification-window-realignment`: Implements physical audio playout isolation, dynamic follow-up timers, and quiet-envelope speech truncation.

### Modified Capabilities
<!-- None -->

## Impact

- **`config.py`**: Added `AppState.ROOM_COOLDOWN_FOLLOW_UP` to the state engine enum.
- **`main.py`**: Major refactoring of the speaking/thinking transition barrier and implementation of the rooms cooldown decay and precision follow-up states.
