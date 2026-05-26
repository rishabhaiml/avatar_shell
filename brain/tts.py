"""
brain/tts.py — Pure ONNXRuntime Kokoro TTS Synthesizer
=======================================================
Replaces sherpa-onnx with a standard onnxruntime InferenceSession that loads
the kokoro.onnx model directly. No native C++ compilation required.

Pipeline:
  sentence (str)
    → espeak phonemization          (phonemizer + espeak-ng)
    → tokens.txt sparse ID mapping  (loaded from disk at startup)
    → ONNX Runtime session.run()    (CUDA → CPU provider chain)
    → PCM int16 bytes               → config.SPEECH_PLAYBACK_QUEUE
"""

import os
import time
import queue
import warnings
import numpy as np
import onnxruntime as ort
import config

# Suppress ORT version/EP warnings that fire on every session init
warnings.filterwarnings("ignore", category=UserWarning, module="onnxruntime")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODEL_DIR = os.path.join(_BASE_DIR, "weights", "kokoro-v1.0")
_MODEL_PATH = os.path.join(_MODEL_DIR, "model.onnx")
_TOKENS_PATH = os.path.join(_MODEL_DIR, "tokens.txt")

# HuggingFace cache for Kokoro-82M voice packs (.pt format, shape [510, 1, 256])
_HF_SNAPSHOT = os.path.join(
    os.path.expanduser("~"),
    ".cache", "huggingface", "hub",
    "models--hexgrad--Kokoro-82M", "snapshots",
)

# Prefer am_michael if cached, fall back to am_adam (verified present on disk)
_VOICE_PREFERENCE = ["am_michael", "am_adam", "am_echo", "af_heart"]

# Maximum phoneme sequence length supported by the voice pack
_MAX_PACK_LEN = 510

# Output sample rate of the Kokoro model
KOKORO_SAMPLE_RATE = 24000


# ---------------------------------------------------------------------------
# Token map loader  (tokens.txt: "<phoneme_char> <id>" — sparse, non-sequential)
# ---------------------------------------------------------------------------
def _load_token_map(tokens_path: str) -> dict[str, int]:
    """Parse tokens.txt into a {char: id} dict. IDs are sparse (gaps exist)."""
    token_map: dict[str, int] = {}
    try:
        with open(tokens_path, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue
                # Format: "<char> <int_id>"  — split from the RIGHT to handle
                # multi-byte Unicode phoneme chars safely
                parts = line.rsplit(" ", 1)
                if len(parts) == 2:
                    ch, idx = parts
                    token_map[ch] = int(idx)
    except FileNotFoundError:
        print(f"❌ tokens.txt not found at {tokens_path}")
    return token_map


# ---------------------------------------------------------------------------
# Voice pack loader  (PyTorch .pt, shape [510, 1, 256])
# ---------------------------------------------------------------------------
def _load_voice_pack() -> "np.ndarray | None":
    """
    Locate the best available .pt voice pack in the HF cache and return it as a
    NumPy float32 array of shape [N, 1, 256].
    """
    try:
        import torch
    except ImportError:
        print("⚠️ torch not available — cannot load .pt voice packs.")
        return None

    if not os.path.isdir(_HF_SNAPSHOT):
        print(f"⚠️ HF snapshot directory not found: {_HF_SNAPSHOT}")
        return None

    # Walk snapshot dirs to find the voices folder
    for snap in sorted(os.listdir(_HF_SNAPSHOT), reverse=True):
        voices_dir = os.path.join(_HF_SNAPSHOT, snap, "voices")
        if not os.path.isdir(voices_dir):
            continue
        for voice_name in _VOICE_PREFERENCE:
            pt_path = os.path.join(voices_dir, f"{voice_name}.pt")
            if os.path.isfile(pt_path):
                pack = torch.load(pt_path, weights_only=True)
                arr = pack.numpy().astype(np.float32)  # [510, 1, 256]
                print(f"🎤 Loaded voice pack: {voice_name!r} — shape {arr.shape}")
                return arr

    print("⚠️ No preferred voice .pt found in HF cache. TTS will use fallback noise vector.")
    return None


# ---------------------------------------------------------------------------
# Phonemizer
# ---------------------------------------------------------------------------
def _phonemize(text: str) -> str:
    """Convert text to IPA phoneme string via espeak-ng backend."""
    try:
        from phonemizer import phonemize
        return phonemize(
            text,
            backend="espeak",
            language="en-us",
            with_stress=True,
            punctuation_marks=";:,.!?—…\"()""",
        )
    except Exception as e:
        print(f"⚠️ Phonemizer failed ({e}). Falling back to raw text characters.")
        return text


# ---------------------------------------------------------------------------
# Text → token ID sequence
# ---------------------------------------------------------------------------
def _text_to_token_ids(text: str, token_map: dict[str, int]) -> list[int]:
    """
    Phonemize text and map each character to its token ID.
    Wraps with start/end token (ID 0) and skips unknown characters silently.
    """
    ps = _phonemize(text)
    token_ids = [0]  # start-of-sequence token
    for ch in ps:
        if ch in token_map:
            token_ids.append(token_map[ch])
        # Unknown IPA chars are silently skipped — the model handles gaps gracefully
    token_ids.append(0)  # end-of-sequence token
    return token_ids


# ---------------------------------------------------------------------------
# ONNX session factory
# ---------------------------------------------------------------------------
def _build_ort_session(model_path: str) -> ort.InferenceSession:
    """
    Build an ONNXRuntime InferenceSession with the best available EP.
    Tries CUDAExecutionProvider first, falls back to CPU.
    Optimizes inter/intra thread bounds to avoid CPU contention.
    """
    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    opts.intra_op_num_threads = max(1, os.cpu_count() // 2)
    opts.inter_op_num_threads = 1
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

    available = ort.get_available_providers()
    providers: list = []
    if "CUDAExecutionProvider" in available:
        providers.append(("CUDAExecutionProvider", {"device_id": 0}))
        print("🚀 Kokoro ONNX: CUDA execution provider available — GPU acceleration enabled.")
    providers.append("CPUExecutionProvider")

    return ort.InferenceSession(model_path, sess_options=opts, providers=providers)


# ---------------------------------------------------------------------------
# Main worker
# ---------------------------------------------------------------------------
def kokoro_synthesizer_worker():
    """
    Asynchronous TTS generation worker.  Pops sentences from SENTENCE_QUEUE,
    runs ONNX inference, and pushes raw int16 PCM bytes to SPEECH_PLAYBACK_QUEUE.

    State flags managed (matching original contract):
        config.SYNTHESIS_ACTIVE
        config.TTS_PROCESSING
        config.BARGE_IN_TRIGGERED
    """
    print("🧠 Initializing Pure ONNX Runtime Kokoro TTS Engine...")

    # -- Load assets at startup (fail fast if model is missing) ---------------
    token_map = _load_token_map(_TOKENS_PATH)
    if not token_map:
        print("❌ Token map empty — TTS layer offline.")
        return

    if not os.path.isfile(_MODEL_PATH):
        print(f"❌ Kokoro ONNX model not found at {_MODEL_PATH} — TTS layer offline.")
        return

    try:
        session = _build_ort_session(_MODEL_PATH)
    except Exception as e:
        print(f"❌ Failed to load Kokoro ONNX session: {e} — TTS layer offline.")
        return

    voice_pack = _load_voice_pack()  # [510, 1, 256] float32 or None

    print("🚀 Pure ONNX Runtime Kokoro Synthesis Engine Ready.")

    # -- Main synthesis loop --------------------------------------------------
    while True:
        try:
            sentence = config.SENTENCE_QUEUE.get(timeout=0.1)
        except queue.Empty:
            continue

        if sentence is None:
            break

        if config.BARGE_IN_TRIGGERED or config.INTERRUPT_FLAG.is_set():
            continue

        config.SYNTHESIS_ACTIVE = True
        config.TTS_PROCESSING = True

        try:
            print(f"🎨 Pure-ONNX Synthesizing: {sentence!r}")
            start_time = time.time()

            # 1. Tokenize
            token_ids = _text_to_token_ids(sentence, token_map)
            if len(token_ids) <= 2:
                # Only start/end tokens — phonemizer produced nothing
                print("⚠️ Empty phoneme sequence — skipping utterance.")
                continue

            seq_len = len(token_ids)

            # 2. Build style vector: indexed by sequence length, clamped to pack size
            if voice_pack is not None:
                style_idx = min(seq_len - 1, _MAX_PACK_LEN - 1)
                style = voice_pack[style_idx]  # [1, 256] float32
            else:
                # Graceful degradation: unit-norm random vector (produces robotic but
                # audible speech — avoids silent failure mode)
                rng = np.random.default_rng(42)
                style = rng.standard_normal((1, 256)).astype(np.float32)
                style /= np.linalg.norm(style)

            if config.INTERRUPT_FLAG.is_set():
                continue

            # 3. ONNX inference
            outputs = session.run(
                None,
                {
                    "tokens": np.array([token_ids], dtype=np.int64),
                    "style":  style,
                    "speed":  np.array([1.0], dtype=np.float32),
                },
            )

            if config.INTERRUPT_FLAG.is_set():
                continue

            # 4. outputs[0] is float32 waveform at 24 kHz — convert to int16 PCM
            audio_wave = outputs[0].flatten()
            if len(audio_wave) == 0:
                print("⚠️ ONNX returned empty audio — skipping.")
                continue

            pcm_i16 = (audio_wave * 32767.0).clip(-32768, 32767).astype(np.int16)

            elapsed = time.time() - start_time
            duration = len(audio_wave) / KOKORO_SAMPLE_RATE
            print(f"⏱️ Pure-ONNX synthesis: {elapsed:.2f}s → {duration:.2f}s of audio for: {sentence!r}")

            config.SPEECH_PLAYBACK_QUEUE.put(pcm_i16.tobytes())

        except Exception as e:
            print(f"❌ Kokoro ONNX synthesis error: {e}")
        finally:
            config.SYNTHESIS_ACTIVE = False
            config.TTS_PROCESSING = False
