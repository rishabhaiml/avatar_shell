## Why

Eliminate interactive conversation failures where the small local LLM omits the `[CLARIFY]` token on inquisitive outputs due to context weight decay or instruction degradation. This leaves the user stranded in wake-word-required mode. Establishing a deterministic, Python-native punctuation fallback ensures a bulletproof Conversational Clarification Loop.

## What Changes

- **System Prompt Calibration**: Calibrate `config.SYSTEM_PROMPT` to give the 1B local model a highly specific blueprint for clarification turns.
- **Punctuation-Aware Fallback**: Update token processing in `brain/llm.py` (`TokenTextFilter`) to programmatically detect question marks (`?`) or follow-up keyword markers and automatically engage `config.WAITING_FOR_CLARIFICATION = True`.
- **Tag Stripping & DB Sanitization**: Guarantee that database logs and playback buffers are completely cleared of `[CLARIFY]` tags, whether written explicitly by the model or matched deterministically.

## Capabilities

### New Capabilities
- `dynamic-question-gating`: Introduces a Python-native punctuation and keyword heuristic fallback to guarantee interactive clarification turn triggers.

### Modified Capabilities
<!-- None -->

## Impact

- **`config.py`**: Updated `SYSTEM_PROMPT` rules.
- **`brain/llm.py`**: Updated `TokenTextFilter` feed and finalize loops to parse punctuation and strip tags before database logging.
