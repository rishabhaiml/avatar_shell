## Context

Small conversational AI models (such as Gemma-1B-IT) have narrow context weights and low attention retention, which frequently causes them to get stuck in circular, repetitive "small-talk" loops when the user speaks monosyllabically. Since B.H.A.I. is a specialized developer companion, conversational drift must be identified and corrected automatically. By evaluating the Type-Token Ratio (TTR) over a sliding conversational ledger, the system can dynamically inject system-level directives to force the model to pivot back to active development workflows.

## Goals / Non-Goals

**Goals:**
- Implement a lightweight, zero-overhead lexical diversity analyzer that runs in less than 1ms before prompt rendering.
- Dynamically inject context intervention blocks to break stagnant conversational loops.

**Non-Goals:**
- Storing full conversation history inside the ledger (which is handled by SQLite conversation history).
- Running external NLP models to evaluate conversational drift.

## Decisions

### Decision 1: Space-Delimited String Tokenization
**Choice**: Convert rolling ledger text to lowercase, strip standard symbols/punctuation, split on spaces, filter out single-character tokens, and calculate TTR.
- **Why**: Extremely fast (takes < 0.1ms), highly robust, and requires zero external dependency installations or model inference latency.
- **Alternatives Considered**: 
  - *Regex-based sub-tokenizers*: Computationally unnecessary for generic TTR scores.
  - *Full embedding distance checking*: Latency is too high for a real-time voice pipeline.

### Decision 2: Dynamic System Prompt Intervention Suffix
**Choice**: Suffix a hidden `[SYSTEM NOTICE: ...]` instruction at the end of the `SYSTEM_PROMPT` when TTR falls below 0.25.
- **Why**: Local LLM prompt engineering shows that terminal instructions (placed at the absolute end of the system context) have the highest attention weights in small-parameter models, guaranteeing gemma-1b follows the intervention.

## Risks / Trade-offs

- **[Risk]** A user discussing a highly repetitive mathematical or coding pattern (e.g. repeating a loop structure) gets falsely flagged as a conversational drift.
  - *Mitigation*: Enforce a strict minimum token limit of **12 meaningful words** and a low TTR ceiling of **0.25 (25% uniqueness)**, which is extremely rare in technical prose but common in circular "yes/okay/nice" exchanges.
