## Why

Evolve B.H.A.I. from a turn-based, purely reactive voice shell into an elegant, proactive full-duplex conversational partner (Jarvis-Symmetry). Currently, the system shuts down or enters IDLE immediately after speaking, requiring the user to speak the wake word again even for quick clarification follow-ups. This change introduces an immediate wake-free follow-up capability when B.H.A.I. asks for clarification.

## What Changes

- **Inline Clarification Parsing**: `TokenTextFilter` streaming parser in `brain/llm.py` parses `[CLARIFY]` cognitive suffix and flags `config.WAITING_FOR_CLARIFICATION`.
- **Automatic State Transition**: In `main.py`, bypass the standard `AppState.IDLE` flow when `config.WAITING_FOR_CLARIFICATION` is True, transitioning directly into a new high-sensitivity `AppState.FOLLOW_UP_LISTENING` state.
- **Clock Re-baselining**: Forcefully re-baseline `listening_start_time` upon entering follow-up listening to prevent clock truncation freezes.
- **Echo-Playout Leakage Guard**: Assert non-blocking hardware flush loops down to absolute zero floor in follow-up listening to prevent echo contamination.

## Capabilities

### New Capabilities
- `interactive-clarification-barrier`: Introduces a proactive, state-aware Conversational Clarification Loop that enables wake-word-free follow-up questions from B.H.A.I.

### Modified Capabilities
<!-- None -->

## Impact

- **`config.py`**: Added state tracking registers (`WAITING_FOR_CLARIFICATION`, `FOLLOW_UP_LISTENING` state handles).
- **`brain/llm.py`**: Token stream parsing to extract the `[CLARIFY]` token.
- **`main.py`**: Core audio state-machine transition modifications, lifecycle barrier checks, and hardware playout flushes.
