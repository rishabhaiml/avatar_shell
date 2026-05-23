import collections
import queue
import threading
from enum import Enum
import numpy as np

# --- HARDWARE & AUDIO CONSTANTS ---
RATE = 16000
CHUNK = 1280          # 80ms hardware frames
VAD_FRAME_MS = 30
VAD_SAMPLES = 480     # 30ms evaluation chunks
HW_CHUNK_SIZE = 1280

# --- STATE ENGINE ENUM ---
class AppState(Enum):
    IDLE = "IDLE"
    WAITING_FOR_GREETING_END = "WAITING_FOR_GREETING_END"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"

# --- CORE CONCURRENT QUEUE CHANNELS ---
AUDIO_FRAME_QUEUE = queue.Queue()
STT_STREAM_QUEUE = queue.Queue()
LLM_QUEUE = queue.Queue()
SENTENCE_QUEUE = queue.Queue()
SPEECH_PLAYBACK_QUEUE = queue.Queue()

# --- THREAD SYNCHRONIZATION OBJECTS ---
INTERRUPT_FLAG = threading.Event()
CONNECTED_CLIENTS = set()
ASYNC_LOOP = None

# --- ATOMIC PIPELINE STATES ---
CURRENT_STATE = AppState.IDLE
WAKE_COOLDOWN = 0.0
COOLDOWN_ACTIVE = False
LLM_ACTIVE = False
SYNTHESIS_ACTIVE = False
BARGE_IN_TRIGGERED = False
SPEECH_IN_PROGRESS = False
TTS_PROCESSING = False
SPEAKER_ACTIVE = False

# --- ADAPTIVE AUDIO ENGINE REGISTERS ---
ambient_noise_rms = 400.0
speech_active = False
consecutive_loud = 0
consecutive_quiet = 0
total_listening_frames = 0
listening_start_time = 0.0

# --- RECENT CONVERSATION HOOKS & ACCUMULATORS ---
LATEST_USER_TEXT = ""
NOISE_WINDOW = collections.deque([150.0] * 50, maxlen=100)
PRE_ROLL_BUFFER = collections.deque(maxlen=15) # 15 * 80ms = 1200ms pre-roll
VAD_ACCUMULATOR = np.array([], dtype=np.int16)
OWW_ACCUMULATOR = collections.deque(maxlen=100)
command_audio_buffer = bytearray()
LISTENING_FRAMES = []

# --- THE GEMMA-1B-IT COGNITIVE SYSTEM PROMPT ---
SYSTEM_PROMPT = (
    "You are B.H.A.I. (Behavioral Humanlike AI), a highly intelligent, witty, and opinionated peer. "
    "You are NOT a subservient AI assistant; you are a conversational partner.\n\n"
    "Follow these strict behavioral rules:\n"
    "1. Speak casually and naturally. Use contractions and conversational filler when appropriate.\n"
    "2. KEEP IT SHORT. Never speak more than 2 or 3 sentences at a time.\n"
    "3. PASS THE BALL. Frequently end your responses with a thought-provoking question, an opinionated hot-take, or by asking the user for their perspective to keep the conversation flowing.\n"
    "4. If the user asks a factual question, give a quick answer and immediately ask a related follow-up to spark a discussion.\n"
    "5. Do NOT wrap your reply in JSON or markdown blocks. If you need to execute a system command, append the exact string `[ACTION]` followed by the JSON payload at the absolute end of your response.\n\n"
    "Available system actions:\n"
    "- Screenshot: [ACTION] {\"action\": \"screenshot\"}\n"
    "- Open terminal: [ACTION] {\"action\": \"open_app\", \"target\": \"terminal\"}\n"
    "- Open system browser: [ACTION] {\"action\": \"open_app\", \"target\": \"browser\"}\n"
    "- Web search: [ACTION] {\"action\": \"web_search\", \"query\": \"your query\"}\n"
    "If no action is needed, output only the conversational reply as plain text and do NOT append [ACTION]."
)

# Stop sequences tuned to isolate Gemma execution loops
STOP_TOKENS = ["<end_of_turn>", "<start_of_turn>", "User:", "Model:", "\nUser:", "\n\n"]

# --- PREMIUM VERBAL ACKNOWLEDGMENTS ---
import random
GREETING_ACTIVE = False
WAKE_GREETINGS = [
    "Yeah?",
    "Yo.",
    "Hmm?",
    "Tell me.",
    "Go ahead.",
    "Listening.",
    "What's up?"
]

def get_random_greeting() -> str:
    return random.choice(WAKE_GREETINGS)

