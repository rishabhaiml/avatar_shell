## 1. Setup & Configuration

- [x] 1.1 Register DYNAMIC_SILENCE_LIMIT and CADENCE_CHECK_IN_PROGRESS global variables in config.py

## 2. Core Implementation

- [x] 2.1 Refactor AppState.FOLLOW_UP_LISTENING block in main.py to handle dynamic threshold scaling
- [x] 2.2 Deploy the background thread partial Whisper suffix sniffer inside main.py
- [x] 2.3 Optimize the Whisper call using beam_size=1 and greedily check for trailing conjunctions

## 3. Verification & Testing

- [x] 3.1 Execute python compilation check on main.py and config.py
- [x] 3.2 Verify turn taking latency matches 600ms on standard turns and adaptive conjunction pauses expand correctly to 1200ms
