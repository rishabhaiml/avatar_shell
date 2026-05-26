import os
import re
import sys
import time
import json
import queue
import subprocess
import urllib.parse
from llama_cpp import Llama
import config
from brain.normalizer import StreamClauseSplitter, LinguisticNormalizer
from memory.engine import BHAIMemoryEngine  # Hook the new memory core

# --- SYSTEM INTEGRATION DRIVER CORE ---
class NativeLinuxAutomator:
    @staticmethod
    def extract_and_execute_json(payload_str: str) -> str:
        try:
            match = re.search(r'\{.*\}', payload_str.strip(), re.DOTALL)
            if not match: 
                return payload_str.strip()
                
            data = json.loads(match.group(0))
            action = data.get("action", "none")
            
            if action == "screenshot":
                subprocess.run(["gnome-screenshot", "-f", "screenshot.png"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "I have successfully captured a desktop screenshot for you."
            elif action == "open_app":
                target_app = data.get("target", "").lower()
                if any(x in target_app for x in ["browser", "chrome", "firefox"]):
                    subprocess.Popen(["xdg-open", "https://google.com"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return "Opening your system browser window right away."
                elif "terminal" in target_app:
                    subprocess.Popen(["gnome-terminal"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return "Launching a new terminal shell session."
                return f"Attempting to launch mapped system binary path: {target_app}"
            elif action == "web_search":
                url = f"https://www.google.com/search?q={urllib.parse.quote(data.get('query', ''))}"
                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Searching the web for: {data.get('query', '')}"
            elif action == "none":
                return data.get("reply", "I am ready and waiting.")
                
            return "Task recognized, executing now."
        except Exception as e: 
            print(f"❌ Automation Error: {e}")
            return "I processed your request, but hit an interface error executing the command."

# --- TOKEN TEXT FILTER AND CHATML STRIPPER ---
class TokenTextFilter:
    def __init__(self):
        self.conversational_buffer = ""
        self.action_buffer = ""
        self.halted = False
        self.potential_action = False

    def feed(self, token: str) -> str:
        # Clean ChatML/prompt tags and Gemma-IT specific boundaries
        for tag in ["<|im_end|>", "<|im_start|>", "<|assistant|>", "<|system|>", "<|user|>", "<start_of_turn>", "<end_of_turn>"]:
            token = token.replace(tag, "")

        if self.halted:
            self.action_buffer += token
            return ""

        # We append the token to either the active stream or the potential action buffer
        for char in token:
            if self.potential_action:
                self.action_buffer += char
                prefix_action = "[ACTION]"
                prefix_clarify = "[CLARIFY]"
                
                # Check if the action_buffer still matches the prefix of [ACTION] or [CLARIFY]
                if prefix_action.startswith(self.action_buffer) or prefix_clarify.startswith(self.action_buffer):
                    if self.action_buffer == prefix_action:
                        self.halted = True
                    elif self.action_buffer == prefix_clarify:
                        config.WAITING_FOR_CLARIFICATION = True
                        self.action_buffer = ""
                        self.potential_action = False
                else:
                    # Deviancy! Flush back
                    self.conversational_buffer += self.action_buffer
                    self.action_buffer = ""
                    self.potential_action = False
            else:
                if char == '[':
                    self.potential_action = True
                    self.action_buffer = char
                else:
                    self.conversational_buffer += char

        # Return whatever conversational text we have collected, and clear the buffer
        emitted = self.conversational_buffer
        self.conversational_buffer = ""
        return emitted

    def finalize(self) -> str:
        if "[CLARIFY]" in self.action_buffer:
            config.WAITING_FOR_CLARIFICATION = True
            self.action_buffer = self.action_buffer.replace("[CLARIFY]", "")
        if not self.halted:
            return self.conversational_buffer + self.action_buffer
        return ""

# --- MAIN INFERENCE THREAD WORKER ---
def llm_worker_thread(model_path: str):
    print("🧠 Initializing In-Process LLaMA Engine (Gemma-1B-IT)...")
    llm_engine = Llama(model_path=model_path, n_ctx=1024, n_threads=4, n_batch=512, verbose=False)
    
    # Instantiate memory agent locally inside generation thread boundary
    memory_agent = BHAIMemoryEngine()
    print("🚀 In-Process LLaMA Engine & Relational Memory Ready.")
    
    enqueued_sentences = []
    has_explicit_clarify = False

    def enqueue_sentence(clean_sentence: str):
        nonlocal has_explicit_clarify
        text = clean_sentence.strip()
        if len(text) <= 1:
            return
            
        # Clean any explicit suffixes if present
        if "[CLARIFY]" in text:
            has_explicit_clarify = True
            text = text.replace("[CLARIFY]", "").strip()
            
        if len(text) > 1:
            config.SENTENCE_QUEUE.put(text)
            enqueued_sentences.append(text)

    while True:
        try:
            # Poll either STT queue or LATEST_USER_TEXT register
            user_input = ""
            try:
                user_input = config.LLM_QUEUE.get(timeout=0.05)
            except queue.Empty:
                if config.LATEST_USER_TEXT != "":
                    user_input = config.LATEST_USER_TEXT
                    config.LATEST_USER_TEXT = ""
                else:
                    time.sleep(0.02)
                    continue

            if not user_input or len(user_input.strip()) < 2:
                continue

            if config.INTERRUPT_FLAG.is_set() or config.BARGE_IN_TRIGGERED:
                continue

            config.LLM_TURN_ACTIVE = True

            # 1. CHRONICLE USER INPUT & FETCH CONTEXT MEMORIES
            memory_agent.log_turn("user", user_input)
            injected_context = memory_agent.retrieve_context(user_input)

            config.LLM_ACTIVE = True
            config.SPEECH_IN_PROGRESS = True
            enqueued_sentences.clear()
            has_explicit_clarify = False
            config.WAITING_FOR_CLARIFICATION = False
            
            # Tier-0 Quick Automation Trigger Check (without running full model)
            normalized_text = user_input.lower()
            tier0_triggered = False
            raw_router_payload = ""

            if "screenshot" in normalized_text:
                raw_router_payload = '{"action": "screenshot"}'
                tier0_triggered = True
            elif "open terminal" in normalized_text:
                raw_router_payload = '{"action": "open_app", "target": "terminal"}'
                tier0_triggered = True
            elif "open browser" in normalized_text:
                raw_router_payload = '{"action": "open_app", "target": "browser"}'
                tier0_triggered = True

            if tier0_triggered:
                ai_response = NativeLinuxAutomator.extract_and_execute_json(raw_router_payload)
                print(f"🤖 Quick Action Response: {ai_response!r}")
                
                # Log turn to memory context
                memory_agent.log_turn("bhai", ai_response)
                
                normalized_response = LinguisticNormalizer.normalize_text(ai_response)
                enqueue_sentence(normalized_response)
                config.LLM_ACTIVE = False
                continue

            splitter = StreamClauseSplitter()
            filter_handler = TokenTextFilter()
            
            # Dynamic Context Budgeting Guardrail (Safe tracking for 1024 max token models)
            MAX_CONTEXT_CHARS = 1200  # ~300 tokens maximum allowance
            if injected_context and len(injected_context) > MAX_CONTEXT_CHARS:
                print("⚠️ Memory context exceeded token budget boundaries! Slicing trailing items...")
                # Keep the personal graph facts, but chop old chat turns to save token space
                if "[RECENT CONVERSATION]:" in injected_context:
                    parts = injected_context.split("[RECENT CONVERSATION]:")
                    profile_part = parts[0]
                    conversation_lines = parts[1].strip().split("\n")
                    
                    # Keep only the last 1 or 2 turns to immediately clear context weight
                    truncated_conversation = "\n".join(conversation_lines[-2:])
                    injected_context = f"{profile_part}\n[RECENT CONVERSATION]:\n{truncated_conversation}"
                    
                    # Final emergency clamp to protect the LLaMA context engine
                    if len(injected_context) > MAX_CONTEXT_CHARS:
                        injected_context = injected_context[:MAX_CONTEXT_CHARS] + "\n...[Context truncated]"

            # Stitch memory context into the hidden system space
            dynamic_system_prompt = config.SYSTEM_PROMPT
            if injected_context:
                dynamic_system_prompt += f"\n\nYou possess the following historical context about the user:\n{injected_context}"
            
            # Format the strict Gemma-IT Token Envelope boundary flags
            formatted_prompt = (
                f"<start_of_turn>user\n[SYSTEM: {dynamic_system_prompt}]\n{user_input}<end_of_turn>\n"
                f"<start_of_turn>model\n"
            )
            
            print(f"🤖 LLM Inference Started with memory context...")
            start_time = time.time()
            first_token = True
            full_response_accumulated = ""
            
            stream = llm_engine(
                formatted_prompt,
                max_tokens=256,
                stream=True,
                stop=config.STOP_TOKENS,
                temperature=0.0
            )
            
            for chunk in stream:
                if config.BARGE_IN_TRIGGERED or config.INTERRUPT_FLAG.is_set():
                    print("💥 BARGE-IN DETECTED: Terminating current inference run.")
                    break
                    
                token_text = chunk["choices"][0]["text"]
                full_response_accumulated += token_text
                
                if first_token and token_text.strip():
                    print(f"⏱️ LLM Time-To-First-Token: {time.time() - start_time:.2f}s")
                    first_token = False
                    
                # Clean prompt tags and filter action indicators
                clean_text = filter_handler.feed(token_text)
                if not clean_text:
                    continue
                    
                # Direct text chunks cleanly to the sentence buffer
                for sentence in splitter.process_chunk(clean_text):
                    enqueue_sentence(sentence)
                        
            # Flush trailing strings left inside the sentence tokenizer memory context
            final_text = filter_handler.finalize()
            for sentence in splitter.process_chunk(final_text):
                if not (config.BARGE_IN_TRIGGERED or config.INTERRUPT_FLAG.is_set()):
                    enqueue_sentence(sentence)
                    
            for sentence in splitter.flush():
                if not (config.BARGE_IN_TRIGGERED or config.INTERRUPT_FLAG.is_set()):
                    enqueue_sentence(sentence)
 
            # If an action was matched and buffered, parse and execute it
            if filter_handler.halted and filter_handler.action_buffer:
                print(f"⚙️ Action detected. Parsing action block: {filter_handler.action_buffer!r}")
                action_msg = NativeLinuxAutomator.extract_and_execute_json(filter_handler.action_buffer)
                if action_msg:
                    normalized_action = LinguisticNormalizer.normalize_text(action_msg)
                    if not (config.BARGE_IN_TRIGGERED or config.INTERRUPT_FLAG.is_set()):
                        enqueue_sentence(normalized_action)
 
            # Determine WAITING_FOR_CLARIFICATION based on the entire turn's final state
            config.WAITING_FOR_CLARIFICATION = False
            if has_explicit_clarify:
                config.WAITING_FOR_CLARIFICATION = True
                print("🔍 [SYSTEM-FIX] Explicit [CLARIFY] tag detected in LLM response.")
            elif enqueued_sentences:
                last_text = enqueued_sentences[-1].strip()
                if last_text.endswith("?") or any(kw in last_text.lower() for kw in ["right?", "agree?", "you think?", "your take?"]):
                    config.WAITING_FOR_CLARIFICATION = True
                    print(f"🔍 [SYSTEM-FIX] Question punctuation/keyword detected in final sentence: {last_text!r}. Engaging Interactive Clarification Loop.")

            # 2. LOG BOT RESPONSE & PASSIVELY PARSE NEW FACTS
            if not (config.BARGE_IN_TRIGGERED or config.INTERRUPT_FLAG.is_set()) and full_response_accumulated.strip():
                clean_log_response = full_response_accumulated.strip()
                if "[CLARIFY]" in clean_log_response:
                    clean_log_response = clean_log_response.replace("[CLARIFY]", "").strip()
                memory_agent.log_turn("bhai", clean_log_response)
                # Learn new things while returning back to idle states
                memory_agent.extract_and_store_entities(user_input)
                
            config.LLM_ACTIVE = False
            config.BARGE_IN_TRIGGERED = False
            config.LLM_TURN_ACTIVE = False
            
        except Exception as e:
            print(f"❌ LLM Thread Exception: {e}")
            config.LLM_ACTIVE = False
            config.LLM_TURN_ACTIVE = False
            time.sleep(0.1)
