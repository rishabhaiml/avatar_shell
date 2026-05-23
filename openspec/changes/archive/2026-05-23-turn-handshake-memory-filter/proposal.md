## Why

Currently, B.H.A.I. has two critical behavioral bugs that disrupt the conversational experience:
1. **Race Condition / Premature IDLE State Transition**: On the first voice capture turn, a synchronization gap between Whisper STT completing its transcription and the LLM worker thread marking itself active causes the main audio thread's timeout machine to prematurely return the system to `IDLE` state before speech generation can occur, locking the user out of conversational wake-word-free follow-up loops.
2. **Memory Context Contamination**: The relational memory engine performs an unweighted similarity search across all historical database entries, bringing in stale development context logs (like visualizer, echo, or audio definitions) during unrelated conversational turns, polluting the LLM's system prompt space.

## What Changes

- **Deterministic Turn Handshake**: Implement `config.LLM_TURN_ACTIVE`, a thread-safe atomic status flag managed directly by the capture loop at the point of transcription dispatch and cleared only after the LLM completes generation and validation, shielding the main thread from premature IDLE transitions during execution gaps.
- **Cognitive Context Relevance Filter**: Integrate a semantic similarity score threshold and recency weight decay inside `brain/llm.py` to discard background memory fragments falling below a strict relevance floor, ensuring B.H.A.I. stays focused on the active topic.

## Capabilities

### New Capabilities
- `turn-synchronization-memory-filter`: Covers the atomic synchronization handshake across STT-LLM thread boundaries and the semantic relevance gating filter for cognitive memory context retrieval.

### Modified Capabilities
<!-- None. Behavior is being introduced as a new subsystem capability to bridge the concurrent STT-LLM gap and cognitive retrieval layers. -->

## Impact

- **Affected Systems**: `main.py` (orchestration, process_audio_queue), `config.py` (application variables), `brain/llm.py` (sentence enqueuing, memory retrieval).
- **APIs & Dependencies**: BHAIMemoryEngine (`memory/engine.py` / sqlite storage), concurrent queue structures.
