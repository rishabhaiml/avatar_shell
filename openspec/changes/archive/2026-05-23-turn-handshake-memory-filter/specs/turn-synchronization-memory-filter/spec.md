## ADDED Requirements

### Requirement: Deterministic Turn Handshake Register
The system SHALL maintain a thread-safe atomic status flag `config.LLM_TURN_ACTIVE` to bridge the STT-to-LLM concurrent processing gap. The voice capture loop at each dispatch gateway MUST set `config.LLM_TURN_ACTIVE = True` before putting tasks to the LLM queue. The background LLM inference worker thread MUST clear `config.LLM_TURN_ACTIVE = False` only upon completing token stream generation, validation, and database history logging. The main thread's audio timeout state machine inside `process_audio_queue()` SHALL never transition `config.CURRENT_STATE` to `AppState.IDLE` while `config.LLM_TURN_ACTIVE` is `True`.

#### Scenario: First turn successfully prevents premature IDLE transition
- **WHEN** the user completes speech capture on the very first turn and the STT dispatcher puts the audio bytes to the STT stream queue
- **THEN** the system sets `config.LLM_TURN_ACTIVE = True`, blocking the main thread's audio queue state machine from resetting the state to `AppState.IDLE` during the LLM startup latency gap, allowing the conversational follow-up loop to successfully engage.

### Requirement: Cognitive Context Relevance Filtering
The semantic memory retrieval engine inside the LLM thread worker SHALL filter and prioritize context memories based on a relevance similarity floor. Any memory log returned by the semantic database that does not cross the similarity threshold MUST be dynamically discarded to prevent irrelevant development logs from contaminating active conversation turns.

#### Scenario: Stale development history is discarded from unrelated turns
- **WHEN** the user asks a question about a watch vs. a coin and the database returns past developer visualizer logs with low semantic similarity scores
- **THEN** the context retrieval engine discards the low-similarity records, keeping B.H.A.I.'s prompt history focused purely on the active watch vs. coin conversation.
