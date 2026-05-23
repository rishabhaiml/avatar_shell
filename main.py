import sys
import os
import ctypes
import json
import asyncio
import threading
import time
import queue
import functools
import warnings
import collections
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import numpy as np
import websockets
import pyaudio
import webrtcvad
import openwakeword
from openwakeword.model import Model
from faster_whisper import WhisperModel
import gi

# --- SUPPRESS ALSA & ONNX CONSOLE SPAM ---
stderr_fd = sys.stderr.fileno()
save_stderr = os.dup(stderr_fd)
devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(devnull, stderr_fd)

try:
    gi.require_version('Gtk', '4.0')
    gi.require_version('WebKit', '6.0')
    from gi.repository import Gtk, GLib
finally:
    # Restore stderr immediately
    os.dup2(save_stderr, stderr_fd)
    os.close(devnull)
    os.close(save_stderr)

warnings.filterwarnings("ignore", category=UserWarning, module="onnxruntime")

# Preload GTK LayerShell for safety
try:
    ctypes.CDLL('libgtk4-layer-shell.so', mode=ctypes.RTLD_GLOBAL)
except OSError:
    pass

import config
from ui.window import AvatarApp
from audio.vad import calculate_frame_rms, run_adaptive_snr_vad
from audio.pipeline import audio_hardware_capture_loop, playback_worker_thread
from brain.llm import llm_worker_thread
from brain.tts import kokoro_synthesizer_worker
from brain.normalizer import LinguisticNormalizer

# Global Engines and Streams
COMMAND_VAD = webrtcvad.Vad(3)
STT_MODEL = None
WAKE_MODEL = None
MIC_STREAM = None

# --- LOCAL STATIC EMBEDDED UI WEBSERVER ---
def start_static_ui_server():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(base_dir, "www")
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args): pass
    handler = functools.partial(QuietHandler, directory=target_dir)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 8000), handler)
        server.serve_forever()
    except OSError: 
        pass

# --- WEBSOCKET REAL-TIME STREAMING RELAY ---
async def ws_handler(websocket):
    config.CONNECTED_CLIENTS.add(websocket)
    try: 
        await websocket.wait_closed()
    finally:
        if websocket in config.CONNECTED_CLIENTS: 
            config.CONNECTED_CLIENTS.remove(websocket)

async def run_server():
    config.ASYNC_LOOP = asyncio.get_running_loop()
    try:
        async with websockets.serve(ws_handler, "127.0.0.1", 8765):
            await asyncio.Future()
    except OSError: 
        pass

def start_ws_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_server())

async def broadcast_payload(payload):
    for ws in list(config.CONNECTED_CLIENTS):
        try:
            await ws.send(payload)
        except Exception:
            pass

def send_ui_state(aa=0.0, ee=0.0, ih=0.0, oh=0.0, ou=0.0, listening=False, thinking=False):
    """
    Sends viseme metrics out over the WebSocket cleanly cross-thread.
    Uses asyncio.run_coroutine_threadsafe to safely cross the thread boundary into the active event loop.
    """
    if not config.CONNECTED_CLIENTS or config.ASYNC_LOOP is None:
        return
    payload = json.dumps({
        "action": "mouth",
        "aa": float(aa),
        "ee": float(ee),
        "ih": float(ih),
        "oh": float(oh),
        "ou": float(ou),
        "listening": bool(listening),
        "thinking": bool(thinking)
    })
    asyncio.run_coroutine_threadsafe(broadcast_payload(payload), config.ASYNC_LOOP)

# Bind the websocket sender callback to config
config.SEND_UI_STATE_CALLBACK = send_ui_state

# --- MIC CAPTURE INPUT CALLBACK ---
def mic_stream_callback(in_data, frame_count, time_info, status):
    """Asynchronously pipes sound card raw frames straight into config queue."""
    try:
        config.AUDIO_FRAME_QUEUE.put(in_data)
    except Exception:
        pass
    return (None, pyaudio.paContinue)

def strip_wake_phrase(text: str) -> str:
    lowered = text.strip()
    for phrase in ["hey jarvis", "jarvis", "hey bhai", "bhai"]:
        if lowered.lower().startswith(phrase):
            return lowered[len(phrase):].strip(" ,.!?")
    return lowered

# --- ASYNCHRONOUS STT TRANSCRIPTION WORKER ---
def stt_worker_thread():
    global STT_MODEL
    print("🧠 Loading Voice Transcription (STT) Whisper Engine...")
    STT_MODEL = WhisperModel(os.getenv("BHAI_WHISPER_MODEL", "base"), device="cpu", compute_type="int8")
    print("🚀 Whisper STT Engine Ready.")
    
    while True:
        try:
            if config.INTERRUPT_FLAG.is_set():
                while not config.STT_STREAM_QUEUE.empty():
                    try: 
                        config.STT_STREAM_QUEUE.get_nowait()
                    except queue.Empty: 
                        break
                time.sleep(0.05)
                continue

            try:
                audio_payload = config.STT_STREAM_QUEUE.get(timeout=0.1)
            except queue.Empty:
                continue

            if config.INTERRUPT_FLAG.is_set():
                continue

            if not audio_payload:
                config.LLM_QUEUE.put("")
                continue

            print("\n🎤 Whisper STT: Transcribing voice buffer...")
            t0 = time.time()
            audio_np = np.frombuffer(audio_payload, dtype=np.int16).astype(np.float32) / 32768.0
            
            segments, _ = STT_MODEL.transcribe(
                audio_np, language="en", task="transcribe", beam_size=5,
                vad_filter=True, condition_on_previous_text=False, temperature=0.0
            )
            segment_list = list(segments)
            elapsed = time.time() - t0
            print(f"⏱️ STT Transcription took {elapsed:.2f}s")
            
            user_text = strip_wake_phrase(" ".join(seg.text for seg in segment_list).strip())
            
            if len(user_text) < 2:
                print("⚠️ Transcript too short. Aborting intent cycle.")
                # Safe state transition back to IDLE
                def set_idle_state():
                    config.CURRENT_STATE = config.AppState.IDLE
                    if config.SEND_UI_STATE_CALLBACK:
                        config.SEND_UI_STATE_CALLBACK(listening=False, thinking=False)
                GLib.idle_add(set_idle_state)
                continue
            
            print(f"👤 User said: {user_text!r}")
            config.LLM_QUEUE.put(user_text)
            
        except Exception as e:
            print(f"❌ STT Worker Thread Error: {e}")
            time.sleep(0.1)

# --- RECURRENT WAKE WORD / MIC DRAINING CLEANUP ---
def flush_hardware_and_onnx():
    global MIC_STREAM, WAKE_MODEL
    if MIC_STREAM:
        try:
            available = MIC_STREAM.get_read_available()
            if available > 0:
                MIC_STREAM.read(available, exception_on_overflow=False)
        except Exception:
            pass
    if WAKE_MODEL:
        try:
            zero_frame = np.zeros(1280, dtype=np.int16)
            for _ in range(5):
                WAKE_MODEL.predict(zero_frame)
        except Exception:
            pass

def trigger_barge_in_interrupt():
    print("\n💥 BARGE-IN TRIGGERED! Interrupting active synthesizers...")
    config.INTERRUPT_FLAG.set()
    
    config.LLM_ACTIVE = False
    config.SYNTHESIS_ACTIVE = False
    
    # Clean outbound message queues
    for q in [config.STT_STREAM_QUEUE, config.LLM_QUEUE, config.SENTENCE_QUEUE, config.SPEECH_PLAYBACK_QUEUE]:
        while not q.empty():
            try: 
                q.get_nowait()
            except queue.Empty: 
                break
                
    flush_hardware_and_onnx()
    
    # Restore pre-roll context
    config.command_audio_buffer = bytearray()
    for chunk in config.PRE_ROLL_BUFFER:
        c_np = np.frombuffer(chunk, dtype=np.int16)
        clean_c = (c_np - np.mean(c_np)).astype(np.int16).tobytes()
        config.command_audio_buffer.extend(clean_c)
    config.PRE_ROLL_BUFFER.clear()
    
    config.VAD_ACCUMULATOR = np.array([], dtype=np.int16)
    config.OWW_ACCUMULATOR.clear()
    config.speech_active = False
    config.consecutive_loud = 0
    config.consecutive_quiet = 0
    config.total_listening_frames = 0
    
    # Safe GTK transition to listening
    def set_listening():
        config.CURRENT_STATE = config.AppState.LISTENING
        if config.SEND_UI_STATE_CALLBACK:
            config.SEND_UI_STATE_CALLBACK(listening=True)
    GLib.idle_add(set_listening)
    
    print("🎧 Listening for your command...")
    config.listening_start_time = time.time()
    config.INTERRUPT_FLAG.clear()

# --- TIMEOUT AUDIO STATE MACHINE ENGINE ---
def process_audio_queue() -> bool:
    """
    Main state machine checks executed within the primary thread context.
    Evaluates volumes and changes states safely in the main loop thread.
    """
    try:
        if config.CURRENT_STATE == config.AppState.ROOM_COOLDOWN_FOLLOW_UP:
            # Flush the mic queue completely to dump lingering playout echo
            while not config.AUDIO_FRAME_QUEUE.empty():
                try:
                    config.AUDIO_FRAME_QUEUE.get_nowait()
                except queue.Empty:
                    break
            
            # Check if 300ms has elapsed
            if time.time() >= config.cooldown_end_time:
                print("⏱️ Room acoustic decay completed. Starting FOLLOW_UP_LISTENING...")
                config.command_audio_buffer = bytearray()
                config.VAD_ACCUMULATOR = np.array([], dtype=np.int16)
                config.LISTENING_FRAMES = []
                config.total_listening_frames = 0
                config.speech_active = False
                config.consecutive_loud = 0
                config.consecutive_quiet = 0
                config.DYNAMIC_SILENCE_LIMIT = 20
                config.CADENCE_CHECK_IN_PROGRESS = False
                
                # Transition to proactive listening and notify visualizer
                config.CURRENT_STATE = config.AppState.FOLLOW_UP_LISTENING
                if config.SEND_UI_STATE_CALLBACK:
                    config.SEND_UI_STATE_CALLBACK(listening=True)
                    
                config.listening_start_time = time.time()
            return True
        while True:
            try:
                raw_chunk = config.AUDIO_FRAME_QUEUE.get_nowait()
            except queue.Empty:
                break

            # Lockout cooldown window checks
            if time.time() < config.WAKE_COOLDOWN:
                config.COOLDOWN_ACTIVE = True
                config.PRE_ROLL_BUFFER.clear()
                while not config.AUDIO_FRAME_QUEUE.empty():
                    try: 
                        config.AUDIO_FRAME_QUEUE.get_nowait()
                    except queue.Empty: 
                        break
                continue

            if config.COOLDOWN_ACTIVE:
                # Flush post cooldown elements
                while not config.AUDIO_FRAME_QUEUE.empty():
                    try: 
                        config.AUDIO_FRAME_QUEUE.get_nowait()
                    except queue.Empty: 
                        break
                config.PRE_ROLL_BUFFER.clear()
                config.COOLDOWN_ACTIVE = False
                print("🎤 B.H.A.I. Core Active. Listening...")
                continue

            if config.GREETING_ACTIVE:
                # Keep internal arrays completely sanitized and ignore incoming audio during greeting
                config.VAD_ACCUMULATOR = np.array([], dtype=np.int16)
                
                # Check if speech is currently in progress or playing using unidirectional hardware flags
                if config.TTS_PROCESSING or config.SPEAKER_ACTIVE or not config.SPEECH_PLAYBACK_QUEUE.empty():
                    if hasattr(process_audio_queue, "greeting_end_time"):
                        delattr(process_audio_queue, "greeting_end_time")
                    continue
                
                if not hasattr(process_audio_queue, "greeting_end_time"):
                    process_audio_queue.greeting_end_time = time.time() + 0.35 # Allow ambient room physics to decay fully
                    print("⏱️ Greeting sound waves cleared. Starting room decay cooldown...")
                
                if time.time() >= process_audio_queue.greeting_end_time:
                    delattr(process_audio_queue, "greeting_end_time")
                    print("⏱️ Room decay completed. Purging microphone loopback echo and starting LISTENING phase...")
                    
                    # 5. CRITICAL PURGE: Clear the queues and internal accumulators COMPLETELY
                    while not config.AUDIO_FRAME_QUEUE.empty():
                        try:
                            config.AUDIO_FRAME_QUEUE.get_nowait()
                        except queue.Empty:
                            break
                            
                    # Reset tracking states cleanly
                    config.speech_active = False
                    config.consecutive_loud = 0
                    config.consecutive_quiet = 0
                    config.total_listening_frames = 0
                    
                    # Remove locks and hand over cleanly to the listening phase
                    config.GREETING_ACTIVE = False
                    
                    # Reset states
                    config.CURRENT_STATE = config.AppState.LISTENING
                    if config.SEND_UI_STATE_CALLBACK:
                        config.SEND_UI_STATE_CALLBACK(listening=True)
                        
                    config.command_audio_buffer = bytearray()
                    for chunk in config.PRE_ROLL_BUFFER:
                        c_np = np.frombuffer(chunk, dtype=np.int16)
                        clean_c = (c_np - np.mean(c_np)).astype(np.int16).tobytes()
                        config.command_audio_buffer.extend(clean_c)
                    config.PRE_ROLL_BUFFER.clear()
                    config.VAD_ACCUMULATOR = np.array([], dtype=np.int16)
                    config.LISTENING_FRAMES = []
                    
                    print("🎧 Listening for your command now... [CLEAN CHANNEL]")
                    config.listening_start_time = time.time()
                continue

            # If the speaker is currently active (playing back responses), discard frames
            # in the IDLE/THINKING states to completely block echo contamination.
            if config.CURRENT_STATE in [config.AppState.IDLE, config.AppState.THINKING] and (config.SPEAKER_ACTIVE or config.TTS_PROCESSING or not config.SPEECH_PLAYBACK_QUEUE.empty()):
                continue

            # Proactive State Routing: Transition to ROOM_COOLDOWN_FOLLOW_UP or IDLE when speaking/thinking ends
            if config.CURRENT_STATE == config.AppState.THINKING and not config.SPEECH_IN_PROGRESS and not config.LLM_TURN_ACTIVE:
                if config.WAITING_FOR_CLARIFICATION:
                    print("\n📣 CLARIFICATION LOOP ACTIVE: Starting playout tail isolation cooldown...")
                    config.WAITING_FOR_CLARIFICATION = False # Consume flag
                    config.cooldown_end_time = time.time() + 0.30
                    config.CURRENT_STATE = config.AppState.ROOM_COOLDOWN_FOLLOW_UP
                else:
                    print("⏱️ Turn completed. Returning to IDLE state.")
                    config.CURRENT_STATE = config.AppState.IDLE
                    if config.SEND_UI_STATE_CALLBACK:
                        config.SEND_UI_STATE_CALLBACK(listening=False, thinking=False)
                continue

            audio_i16 = np.frombuffer(raw_chunk, dtype=np.int16)
            
            # Dynamic Ambient Baseline (EMA) tracking during IDLE state
            if config.CURRENT_STATE == config.AppState.IDLE:
                chunk_rms = float(np.sqrt(np.mean(np.square(audio_i16.astype(np.float32)))))
                config.ambient_noise_rms = min(1500.0, (0.95 * config.ambient_noise_rms) + (0.05 * chunk_rms))

            volume = float(np.sqrt(np.mean(np.square(audio_i16.astype(np.float32)))))
            if volume < 1000:
                config.NOISE_WINDOW.append(volume)
            noise_floor = float(np.percentile(config.NOISE_WINDOW, 20))

            if config.CURRENT_STATE in [config.AppState.IDLE, config.AppState.THINKING] and time.time() > config.WAKE_COOLDOWN:
                config.PRE_ROLL_BUFFER.append(raw_chunk)
                
                # Check Wake word predictions
                prediction = WAKE_MODEL.predict(audio_i16)
                config.OWW_ACCUMULATOR.append(audio_i16)
                score = max([float(v) for v in prediction.values()], default=0.0)

                if score >= 0.55:
                    if config.CURRENT_STATE == config.AppState.THINKING:
                        trigger_barge_in_interrupt()
                    else:
                        print(f"\n🚀 WAKE WORD TRIGGERED! (Score: {score:.2f})")
                        
                        # 1. SNAPPY VERBAL GREETING INITIALIZATION
                        config.GREETING_ACTIVE = True
                        config.SPEECH_IN_PROGRESS = True  # Lock orchestrator handshake
                        
                        # 2. Flush any pre-existing frame buffers to wipe background noises
                        while not config.AUDIO_FRAME_QUEUE.empty():
                            try:
                                config.AUDIO_FRAME_QUEUE.get_nowait()
                            except queue.Empty:
                                break

                        # 3. Choose a random quick expression and pass it directly to the synthesis engine
                        greeting_text = config.get_random_greeting()
                        print(f"🗣️ B.H.A.I. Acknowledgment: {greeting_text!r}")
                        
                        # Put directly to SENTENCE_QUEUE bypassing the LLM thread block completely
                        config.SENTENCE_QUEUE.put(greeting_text)
                        
                        # 4. Set state to WAITING_FOR_GREETING_END (non-blocking)
                        config.CURRENT_STATE = config.AppState.WAITING_FOR_GREETING_END
                    break

                if config.CURRENT_STATE == config.AppState.THINKING:
                    continue

            elif config.CURRENT_STATE == config.AppState.THINKING:
                continue

            elif config.CURRENT_STATE == config.AppState.SPEAKING:
                continue

            elif config.CURRENT_STATE in [config.AppState.LISTENING, config.AppState.FOLLOW_UP_LISTENING]:
                # High-Fidelity Local DC-Offset Removal Filter
                chunk_np = np.frombuffer(raw_chunk, dtype=np.int16)
                clean_np = (chunk_np - np.mean(chunk_np)).astype(np.int16)
                clean_chunk = clean_np.tobytes()

                config.LISTENING_FRAMES.append(clean_chunk)
                config.command_audio_buffer.extend(clean_chunk)
                config.total_listening_frames += 1

                # Sub-chunk slicing for WebRTC VAD inputs using clean centered samples
                config.VAD_ACCUMULATOR = np.concatenate((config.VAD_ACCUMULATOR, clean_np))
                while len(config.VAD_ACCUMULATOR) >= 480:
                    sub_chunk = config.VAD_ACCUMULATOR[:480]
                    config.VAD_ACCUMULATOR = config.VAD_ACCUMULATOR[480:]

                    sub_chunk_arr = np.frombuffer(sub_chunk, dtype=np.int16) if isinstance(sub_chunk, bytes) else sub_chunk
                    sub_bytes = sub_chunk.tobytes()
                    
                    # We run the VAD but ignore standard VAD return triggers for follow-up listening
                    should_trigger = run_adaptive_snr_vad(sub_bytes, COMMAND_VAD)
                    if config.CURRENT_STATE == config.AppState.LISTENING and should_trigger:
                        break
                
                if config.CURRENT_STATE == config.AppState.FOLLOW_UP_LISTENING:
                    # 1. Trailing silence cut-off check (dynamic limit frames)
                    if config.speech_active:
                        if config.consecutive_quiet == 1 and not config.CADENCE_CHECK_IN_PROGRESS:
                            # User just paused! Spawn background thread to check trailing cadence
                            config.CADENCE_CHECK_IN_PROGRESS = True
                            
                            def check_trailing_cadence(audio_snapshot):
                                global STT_MODEL
                                try:
                                    if STT_MODEL:
                                        audio_np = np.frombuffer(audio_snapshot, dtype=np.int16).astype(np.float32) / 32768.0
                                        segments, _ = STT_MODEL.transcribe(audio_np, language="en", beam_size=1)
                                        partial_text = " ".join(seg.text for seg in segments).strip().lower()
                                        
                                        CONJUNCTIONS = ["because", "but", "so", "and", "or", "if", "then", "like"]
                                        words = partial_text.split()
                                        if words and words[-1] in CONJUNCTIONS:
                                            config.DYNAMIC_SILENCE_LIMIT = 40  # Scale limit to 1200ms
                                            print(f"🔍 [CADENCE-BACKOFF] Trailing conjunction detected ({words[-1]!r}). Scaling silence floor to 1200ms.")
                                except Exception as e:
                                    pass
                                finally:
                                    config.CADENCE_CHECK_IN_PROGRESS = False

                            import threading
                            snapshot_bytes = bytes(config.command_audio_buffer)
                            threading.Thread(target=check_trailing_cadence, args=(snapshot_bytes,), daemon=True).start()

                        if config.consecutive_quiet >= config.DYNAMIC_SILENCE_LIMIT:
                            elapsed = time.time() - config.listening_start_time
                            print(f"⏱️ Voice capture completed (Snappy Follow-up) in {elapsed:.2f}s (Limit: {config.DYNAMIC_SILENCE_LIMIT}). Dispatching...")
                            
                            if config.SEND_UI_STATE_CALLBACK:
                                config.SEND_UI_STATE_CALLBACK(listening=False, thinking=True)
                            config.CURRENT_STATE = config.AppState.THINKING
                            config.SPEECH_IN_PROGRESS = True
                            config.LLM_TURN_ACTIVE = True
                            config.STT_STREAM_QUEUE.put(bytes(config.command_audio_buffer))
                            
                            config.OWW_ACCUMULATOR.clear()
                            config.PRE_ROLL_BUFFER.clear()
                            if WAKE_MODEL:
                                try: 
                                    WAKE_MODEL.reset()
                                except Exception: 
                                    pass
                            config.WAKE_COOLDOWN = time.time() + 1.5
                            break
                    
                    # 2. Maximum dynamic open mic timeout check (5.0 seconds)
                    elif time.time() - config.listening_start_time >= 5.0:
                        print("⚠️ Follow-up open mic timeout (5.0s reached) without completed speech. Standing down.")
                        if config.SEND_UI_STATE_CALLBACK:
                            config.SEND_UI_STATE_CALLBACK(listening=False)
                        config.WAKE_COOLDOWN = time.time() + 1.0
                        config.COOLDOWN_ACTIVE = True
                        config.CURRENT_STATE = config.AppState.IDLE
                        config.LISTENING_FRAMES.clear()
                        break
                
                else:  # Standard AppState.LISTENING checks
                    # Grace timeout check
                    if not config.speech_active and config.total_listening_frames > 200:
                        print("⚠️ Grace period expired. No speech detected.")
                        if config.SEND_UI_STATE_CALLBACK:
                            config.SEND_UI_STATE_CALLBACK(listening=False)
                        config.WAKE_COOLDOWN = time.time() + 1.5
                        config.COOLDOWN_ACTIVE = True
                        config.CURRENT_STATE = config.AppState.IDLE
                        config.LISTENING_FRAMES.clear()
                        break

                    # Completed conversational turn check (consecutive silence)
                    if config.speech_active and config.consecutive_quiet >= 66:
                        elapsed = time.time() - config.listening_start_time
                        print(f"⏱️ Voice capture completed in {elapsed:.2f}s. Dispatching to STT...")
                        
                        if config.SEND_UI_STATE_CALLBACK:
                            config.SEND_UI_STATE_CALLBACK(listening=False, thinking=True)
                        config.CURRENT_STATE = config.AppState.THINKING
                        config.SPEECH_IN_PROGRESS = True
                        config.LLM_TURN_ACTIVE = True
                        config.STT_STREAM_QUEUE.put(bytes(config.command_audio_buffer))
                        
                        config.OWW_ACCUMULATOR.clear()
                        config.PRE_ROLL_BUFFER.clear()
                        if WAKE_MODEL:
                            try: 
                                WAKE_MODEL.reset()
                            except Exception: 
                                pass
                        config.WAKE_COOLDOWN = time.time() + 1.5
                        break

                    # Absolute maximum recording threshold check (24 seconds)
                    if config.total_listening_frames >= 300:
                        elapsed = time.time() - config.listening_start_time
                        print(f"⏱️ Maximum recording limit reached ({elapsed:.2f}s). Dispatching...")
                        
                        if config.SEND_UI_STATE_CALLBACK:
                            config.SEND_UI_STATE_CALLBACK(listening=False, thinking=True)
                        config.CURRENT_STATE = config.AppState.THINKING
                        config.SPEECH_IN_PROGRESS = True
                        config.LLM_TURN_ACTIVE = True
                        config.STT_STREAM_QUEUE.put(bytes(config.command_audio_buffer))
                        
                        config.OWW_ACCUMULATOR.clear()
                        config.PRE_ROLL_BUFFER.clear()
                        if WAKE_MODEL:
                            try: 
                                WAKE_MODEL.reset()
                            except Exception: 
                                pass
                        config.WAKE_COOLDOWN = time.time() + 1.5
                        break

    except Exception as e:
        print(f"⚠️ Audio state machine tracker crash handled gracefully: {e}")
    return True

# --- SYSTEM INITIALIZATION BOOTSTRAP ---
def main():
    global WAKE_MODEL, MIC_STREAM
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("🧹 Running background database optimization pass...")
    try:
        from memory.engine import BHAIMemoryEngine
        boot_cleaner = BHAIMemoryEngine()
        # Prune historical rolling entries older than 14 days and clear unused pages
        boot_cleaner.clear_stale_context(maximum_days=14)
        print("✅ Database optimization complete. Running threads.")
    except Exception as e:
        print(f"⚠️ Memory engine optimization failed at boot: {e}")

    # Pre-load Wake Word ONNX engine model
    jarvis_model_path = next(p for p in openwakeword.get_pretrained_model_paths() if "hey_jarvis" in p)
    WAKE_MODEL = Model(wakeword_model_paths=[jarvis_model_path], vad_threshold=0.25)
    
    # Initialize light microservers inside background helper threads
    threading.Thread(target=start_static_ui_server, daemon=True).start()
    threading.Thread(target=start_ws_server, daemon=True).start()

    # Launch daemon infrastructure processing thread systems
    threading.Thread(target=stt_worker_thread, daemon=True).start()
    threading.Thread(target=llm_worker_thread, args=(os.path.join(base_dir, "model.gguf"),), daemon=True).start()
    threading.Thread(target=kokoro_synthesizer_worker, daemon=True).start()
    
    # Initialize physical Sound Card PortAudio drivers
    pa = pyaudio.PyAudio()
    
    # Open mic record streaming pipeline
    threading.Thread(target=audio_hardware_capture_loop, args=(pa,), daemon=True).start()
    
    # Open speaker playback pipeline (attaching wake model reset as flush_callback)
    threading.Thread(target=playback_worker_thread, args=(pa, flush_hardware_and_onnx), daemon=True).start()

    print("\n🎤 B.H.A.I. Core Active. Say 'Hey Jarvis'...")

    # Hook the state machine timer loop into the primary GTK thread context
    GLib.timeout_add(30, process_audio_queue)

    # Launch primary GTK Application loop
    try:
        app = AvatarApp()
        sys.exit(app.run(sys.argv))
    except KeyboardInterrupt:
        print("\n⚙️ Shutting down Shell cleanly down via termination sequences.")
    finally:
        try:
            pa.terminate()
        except Exception:
            pass
        sys.exit(0)

if __name__ == "__main__":
    main()