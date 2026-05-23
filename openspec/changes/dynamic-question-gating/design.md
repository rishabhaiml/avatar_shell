## Context

Small 1B parameter models like Gemma-1B-IT running locally have thin context weights and can suffer instruction degradation. In longer sessions, they frequently omit the literal `[CLARIFY]` suffix when asking follow-up questions. A programmatic fallback inside the token streaming pipeline (`brain/llm.py`) is required to detect inquisitive punctuation and tags and deterministically engage the clarification loop.

## Goals / Non-Goals

**Goals:**
- Update `config.SYSTEM_PROMPT` to reinforce model tagging compliance.
- Modify `TokenTextFilter` in `brain/llm.py` to intercept completed sentence boundaries.
- Track interrogation marks (`?`) and colloquial inquisitive tags (`"right?"`, `"agree?"`, etc.) at sentence termination.
- Set `config.WAITING_FOR_CLARIFICATION = True` upon fallback match and strip any tags before audio playout and SQLite database logging.

**Non-Goals:**
- Complex natural language grammar checking or semantic intent parsing.
- Altering physical VAD/RMS states or audio capture loops.

## Decisions

### 1. Punctuation Sentence-End Heuristics
- **Choice**: Scan sentence boundaries for terminal `"?"` and colloquial trailing keywords inside `TokenTextFilter`.
- **Rationale**: Since `TokenTextFilter` is already splitting generated text streams into printable/spoken sentences, checking boundaries is completely free, O(1), and incredibly accurate for voice conversations.

## Risks / Trade-offs

- **[Risk]** False Positives (user quotes containing "?") → **[Mitigation]** The check is constrained strictly to the end of the stripped sentence, which is highly robust for voice dialogue.
