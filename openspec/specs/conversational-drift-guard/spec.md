# conversational-drift-guard Specification

## Purpose
TBD - created by archiving change conversational-drift-guard. Update Purpose after archive.
## Requirements
### Requirement: Rolling Dialogue Ledger
The inference engine SHALL maintain a rolling conversation history ledger in the global register `config.CONVERSATIONAL_HISTORY_LEDGER`. The ledger MUST capture exactly the last 6 conversational turns (representing the last 3 user inputs and the last 3 assistant outputs) as dictionary items `{"role": "user/bhai", "text": "..."}`.

#### Scenario: Dialogue turns are tracked within a sliding window of 6 items
- **WHEN** the assistant finishes generating a response and enqueues it to the conversation history
- **THEN** the system appends the response to `config.CONVERSATIONAL_HISTORY_LEDGER` and discards the oldest entry if the ledger exceeds a maximum length of 6 entries.

### Requirement: Lexical Diversity Evaluation and Prompt Context Override
Prior to generating LLM prompt templates, the system SHALL tokenize the combined text inside `config.CONVERSATIONAL_HISTORY_LEDGER` (excluding stopwords or short symbols) and calculate the Type-Token Ratio (TTR):
$$\text{TTR} = \frac{\text{Count of Unique Words}}{\text{Total Count of Words}}$$
If the calculated TTR score is less than `0.25` over a minimum word window of 12 tokens, the system MUST flag a conversational drift breach and append a hidden system intervention directive to B.H.A.I.'s `SYSTEM_PROMPT` instructing the model to break circular, stagnant small-talk cycles and immediately pivot back to software development, project architecture, and coding workflows.

#### Scenario: Low TTR triggers system override directive
- **WHEN** the user provides brief, repetitive inputs like "Nice", "Yes", "Okay" and the computed TTR is 0.18 over 15 words
- **THEN** B.H.A.I. injects the hidden drift-guard prompt directive, forcing gemma-1b to discard pleasantries and pivot the discussion back to software development topics.

