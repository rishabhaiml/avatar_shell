## 1. Setup & Config Extension

- [x] 1.1 Add AppState.FOLLOW_UP_LISTENING state in config.py
- [x] 1.2 Add WAITING_FOR_CLARIFICATION register in config.py
- [x] 1.3 Add [CLARIFY] rule instructions to SYSTEM_PROMPT in config.py

## 2. Inline Suffix Parser Implementation

- [x] 2.1 Update TokenTextFilter in brain/llm.py to detect [CLARIFY] inline tokens
- [x] 2.2 Configure B.H.A.I. LLM worker to set config.WAITING_FOR_CLARIFICATION on detection
- [x] 2.3 Strip [CLARIFY] tokens from spoken sentence streams in TokenTextFilter

## 3. Audio State Machine Refactoring

- [x] 3.1 Refactor process_audio_queue in main.py to handle AppState.FOLLOW_UP_LISTENING
- [x] 3.2 Implement non-blocking queue flushes on clarification loop entry in main.py
- [x] 3.3 Re-baseline listening_start_time upon transition to FOLLOW_UP_LISTENING to prevent clock freezes

## 4. Verification & Testing

- [x] 4.1 Execute python compilation check on modified config.py, main.py, and brain/llm.py
- [x] 4.2 Validate proactive wake-free conversational turns manually with LLM logs
