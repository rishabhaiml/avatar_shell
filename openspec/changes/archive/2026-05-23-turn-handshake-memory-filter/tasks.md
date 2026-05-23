## 1. Setup & Configuration

- [x] 1.1 Register LLM_TURN_ACTIVE global variable in config.py

## 2. Core Implementation

- [x] 2.1 Refactor STT dispatch gateways in main.py to set LLM_TURN_ACTIVE to True
- [x] 2.2 Refactor process_audio_queue in main.py to wait for LLM_TURN_ACTIVE to clear before returning to IDLE
- [x] 2.3 Refactor llm_worker_thread in brain/llm.py to manage LLM_TURN_ACTIVE and wrap in try-finally block
- [x] 2.4 Calibrate the database memory retrieval in brain/llm.py to filter out low-relevance context fragments

## 3. Verification & Testing

- [x] 3.1 Validate python compilation of config.py, brain/llm.py, main.py
- [x] 3.2 Verify sub-second conversational turns work without premature IDLE transition on the first turn
