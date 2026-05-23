## Why

Small local LLMs (like Gemma-1B-IT) have narrow context attention spans, which frequently causes them to fall into repetitive small-talk loops when conversational inputs are brief or monosyllabic (e.g., "Yes", "Okay"). Implementing a real-time Conversational Drift Guard will detect repetitive conversational stagnation using Type-Token Ratio (TTR) math and inject custom cognitive directives to steer the assistant back to high-utility programming or architectural development workflows.

## What Changes

- **Conversational History Ledger**: Register `config.CONVERSATIONAL_HISTORY_LEDGER` to track the last 6 turns (3 user + 3 assistant).
- **Lexical Diversity Evaluator**: Calculate the Type-Token Ratio (TTR) over the rolling ledger words.
- **Context Injection Override**: Set `drift_intervention_active = True` if TTR falls below `0.25` with at least 12 words, and append a hidden system directive to B.H.A.I.'s system prompt telling the model to break repetitive cycles and pivot back to actionable software engineering and project topics.

## Capabilities

### New Capabilities
- `conversational-drift-guard`: Covers rolling conversational turn ledgers, real-time TTR lexical analysis, and hidden prompt context override interventions.

### Modified Capabilities
<!-- None. Behavior is being introduced as a new subsystem capability to protect LLM conversational utility. -->

## Impact

- **Affected Systems**: `config.py` (rolling history ledger register), `brain/llm.py` (dialogue ledger tracking, TTR math, and system prompt formatting).
- **APIs & Dependencies**: String processing utilities.
