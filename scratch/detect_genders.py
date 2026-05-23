import wave
import numpy as np
import os

def estimate_pitch(wav_path):
    with wave.open(wav_path, "rb") as wav:
        params = wav.getparams()
        n_channels, sampwidth, framerate, n_frames = params[:4]
        content = wav.readframes(n_frames)
        samples = np.frombuffer(content, dtype=np.int16).astype(np.float32)
        
    # Standard autocorrelation-based pitch estimation
    # Focus on standard human vocal range: 50 Hz to 300 Hz
    min_lag = int(framerate / 300)
    max_lag = int(framerate / 50)
    
    # We will analyze frames of 1024 samples
    frame_size = 1024
    hop_size = 512
    pitches = []
    
    for i in range(0, len(samples) - frame_size, hop_size):
        frame = samples[i : i + frame_size]
        if np.max(np.abs(frame)) < 500:  # Silence
            continue
            
        # Autocorrelation
        corr = np.correlate(frame, frame, mode='full')
        corr = corr[len(corr)//2:]
        
        # Find peak in the lag range
        r_range = corr[min_lag:max_lag]
        if len(r_range) == 0:
            continue
        peak_lag = np.argmax(r_range) + min_lag
        pitch = framerate / peak_lag
        pitches.append(pitch)
        
    if not pitches:
        return 0.0
    return float(np.median(pitches))

# Analyze speakers 0 to 10
for sid in range(11):
    wav_path = f"scratch/voices/speaker_{sid}.wav"
    if os.path.exists(wav_path):
        pitch = estimate_pitch(wav_path)
        gender = "Male (Low Pitch)" if pitch < 165 else "Female (High Pitch)"
        print(f"Speaker {sid}: Est. Pitch = {pitch:.1f} Hz -> likely {gender}")
