## 1. Config Updates

- [x] 1.1 Add AppState.ROOM_COOLDOWN_FOLLOW_UP in config.py

## 2. Core State Machine Realignment

- [x] 2.1 Refactor speaking/thinking turn resolution to transition to ROOM_COOLDOWN_FOLLOW_UP in main.py
- [x] 2.2 Implement AppState.ROOM_COOLDOWN_FOLLOW_UP state with 300ms sleep and mic buffer purge in main.py
- [x] 2.3 Refactor AppState.FOLLOW_UP_LISTENING state with 5.0s maximum timer, trailing quiet tracking, and Whisper STT queue dispatch in main.py

## 3. Verification & Testing

- [x] 3.1 Execute python compilation check on modified config.py and main.py
- [x] 3.2 Validate Conversational Clarification Loop manually and verify playout tail isolation
