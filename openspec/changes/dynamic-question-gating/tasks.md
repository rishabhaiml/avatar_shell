## 1. Prompt Calibration

- [ ] 1.1 Reinforce clarification turning guidelines in config.SYSTEM_PROMPT

## 2. Token Pipeline Fallbacks

- [ ] 2.1 Implement punctuation endswith("?") fallback detection in brain/llm.py
- [ ] 2.2 Implement inquisitive keywords fallback detection in brain/llm.py
- [ ] 2.3 Sanitize the SQLite log response string to completely strip [CLARIFY] in brain/llm.py

## 3. Verification & Testing

- [ ] 3.1 Execute python compilation check on modified config.py and brain/llm.py
- [ ] 3.2 Validate [SYSTEM-FIX] punctuation fallbacks manually with B.H.A.I. question turns
