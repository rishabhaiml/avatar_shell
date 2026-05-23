import numpy as np
import config

def calculate_frame_rms(audio_bytes: bytes) -> float:
    audio_arr = np.frombuffer(audio_bytes, dtype=np.int16)
    if len(audio_arr) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio_arr.astype(np.float32)))))

def run_adaptive_snr_vad(audio_chunk: bytes, command_vad_engine) -> bool:
    """
    Evaluates raw chunk allocations using Clamped SNR math and Rustle Rejection constraints.
    Returns True if user speaking loop breaks successfully to trigger processing.
    """
    sub_volume = calculate_frame_rms(audio_chunk)
    
    # Establish a clamped gate relative to the moving background line tracker
    dynamic_speech_gate = min(3500.0, max(800.0, config.ambient_noise_rms * 2.0))
    
    # Combine frequency checking with structural amplitude thresholds
    is_valid_speech = command_vad_engine.is_speech(audio_chunk, config.RATE) and (sub_volume > dynamic_speech_gate)
    
    # Log VAD calculations periodically (e.g. if speech is active or on periodic checks)
    # The parent loop will print state as necessary. We can log here too.
    
    if is_valid_speech:
        config.consecutive_loud += 1
        if config.consecutive_loud >= 3:
            config.speech_active = True
            
        # RUSTLE REJECTION: Require a sustained loud burst to reset the silence counter
        if config.consecutive_loud >= 5:
            config.consecutive_quiet = 0
    else:
        config.consecutive_loud = 0
        if config.speech_active:
            config.consecutive_quiet += 1
            
    config.total_listening_frames += 1
    
    # Check if the user has finished their conversational turn
    if config.speech_active and config.consecutive_quiet >= 66:
        print("🎵 Speech finished. Transitioning back to IDLE state processing channels.")
        return True
        
    # Check if the initial connection grace window has timed out
    if not config.speech_active and config.total_listening_frames > 200:
        print("⚠️ Grace period expired. No speech detected.")
        return True
        
    return False
