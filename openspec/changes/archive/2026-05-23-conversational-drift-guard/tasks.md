## 1. Setup & Configuration

- [ ] 1.1 Register CONVERSATIONAL_HISTORY_LEDGER global variable in config.py

## 2. Core Implementation

- [ ] 2.1 Refactor llm_worker_thread in brain/llm.py to append user inputs and bot outputs to the ledger
- [ ] 2.2 Implement the Type-Token Ratio lexical diversity mathematical evaluation in brain/llm.py
- [ ] 2.3 Refactor system prompt building to inject hidden system directives during a drift breach

## 3. Verification & Testing

- [ ] 3.1 Execute python compilation check on main.py and brain/llm.py
- [ ] 3.2 Verify TTR scores calculate correctly and hidden prompt directives steer Gemma back to project workflows
