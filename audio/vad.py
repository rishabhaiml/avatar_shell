import numpy as np
import config


def calculate_frame_rms(audio_np: np.ndarray) -> float:
    """Return RMS energy of a signed int16 array as a float."""
    if len(audio_np) == 0:
        return 0.0
    return float(np.sqrt(np.mean(audio_np.astype(np.float32) ** 2)))


def run_adaptive_snr_vad(audio_np: np.ndarray, ambient_noise_rms: float | None = None) -> bool:
    """
    Pure-Python Statistical Voice Activity Detection.

    Evaluates short-term signal energy against a localized ambient noise baseline
    using a clamped SNR threshold gate — no native C-extension required.

    Returns True when the utterance boundary has been reached (speech finished),
    mirroring the original contract used by process_audio_queue callers.
    """
    if ambient_noise_rms is None:
        ambient_noise_rms = config.ambient_noise_rms

    frame_rms = calculate_frame_rms(audio_np)

    # Clamped dynamic speech gate: never below 800 or above 3500
    dynamic_gate = min(3500.0, max(800.0, ambient_noise_rms * 2.0))
    is_valid_speech = frame_rms > dynamic_gate

    if is_valid_speech:
        config.consecutive_loud += 1
        # Require a sustained burst before marking speech active (rustle rejection)
        if config.consecutive_loud >= 3:
            config.speech_active = True
        # Reset silence counter only after a clear sustained loud burst
        if config.consecutive_loud >= 5:
            config.consecutive_quiet = 0
    else:
        config.consecutive_loud = 0
        if config.speech_active:
            config.consecutive_quiet += 1

    config.total_listening_frames += 1

    # Utterance-complete signal: sustained silence after active speech
    if config.speech_active and config.consecutive_quiet >= 66:
        print("🎵 Speech finished. Transitioning back to IDLE state processing channels.")
        return True

    # Grace-period expiry: no speech detected within the initial window
    if not config.speech_active and config.total_listening_frames > 200:
        print("⚠️ Grace period expired. No speech detected.")
        return True

    return False
