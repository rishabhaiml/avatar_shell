## Context

The current voice coordinator in B.H.A.I. has two critical regressions:
1. **Thread Synchronization Gap**: When Whisper STT transcribes user speech, it places the intent string into the `config.LLM_QUEUE` and immediately switches `config.CURRENT_STATE = AppState.THINKING`. There is a brief latency gap before the background `llm_worker_thread` picks up the task and starts generation. During this gap, the main thread's audio timeout loop (`process_audio_queue()`) executes, sees that all speaker playback indicators are currently inactive, and prematurely returns the system to `AppState.IDLE`.
2. **Memory Context Contamination**: Unweighted cosine similarity searches across the Sqlite memory database pull in stale developer log terms from past runs, bleeding unrelated background records into new conversation turns.

## Goals / Non-Goals

**Goals:**
- Eliminate the microsecond race condition gap between STT dispatch and LLM activation, preventing premature IDLE transitions on the first conversational turn.
- Establish a high-relevance similarity score filter on semantic memory retrieval to isolate conversational context.

**Non-Goals:**
- Upgrading or changing the underlying database engine (SQLite/Vector).
- Modifying the acoustic WebRTC VAD or Sherpa Kokoro playback code.

## Decisions

### Decision 1: Thread-Safe State Handshake Register
**Choice**: Introduce a global coordination register `config.LLM_TURN_ACTIVE` set to `True` on the main thread at the exact moment of STT dispatch, and set to `False` on the LLM thread only when generation, validation, and db logging completely wrap up.
- **Why**: Atomic state control on the dispatching thread is the only way to close concurrent race windows before the worker thread can execute.
- **Alternatives Considered**: 
  - *Checking LLM_QUEUE size*: Brittle because the queue might become empty the moment the LLM thread retrieves the item, but before it starts token generation.
  - *Direct LLM_ACTIVE checking*: Suffers from the exact concurrent gap described (since `LLM_ACTIVE` is set on the worker thread, not the dispatch thread).

### Decision 2: Cosine Similarity Gating Filter for SQLite Memory
**Choice**: Configure a strict cosine similarity floor (e.g. `relevance >= 0.70` or similar threshold) inside `memory/engine.py` retrieval or during context stitching in `brain/llm.py`. Any retrieved historical memory that falls below this floor is discarded.
- **Why**: Keeps the LLM prompt space pristine and focused on the active session's immediate topic.
- **Alternatives Considered**:
  - *Disabling historical memories*: Out of scope because B.H.A.I.'s core conversational capability relies on personal facts retrieval.
  - *Full weight retraining*: Computationally too heavy for a local 1B parameter model.

## Risks / Trade-offs

- **[Risk]** The LLM thread crashes or hits an unhandled exception before it can reset `config.LLM_TURN_ACTIVE = False`, leaving B.H.A.I. permanently stuck in the `THINKING` state.
  - *Mitigation*: Wrap the entire generation and validation loop in a robust, airtight `try...finally` block inside `brain/llm.py` to guarantee that `config.LLM_TURN_ACTIVE` is reset to `False` even on execution failures.
