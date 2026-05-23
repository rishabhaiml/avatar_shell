import os
import wave
import numpy as np
import sherpa_onnx

model_dir = "weights/kokoro-v1.0"
cfg = sherpa_onnx.OfflineTtsConfig(
    model=sherpa_onnx.OfflineTtsModelConfig(
        kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=os.path.join(model_dir, "model.onnx"),
            voices=os.path.join(model_dir, "voices.bin"),
            tokens=os.path.join(model_dir, "tokens.txt"),
            data_dir=os.path.join(model_dir, "espeak-ng-data"),
            lexicon=os.path.join(model_dir, "lexicon-us-en.txt"),
            dict_dir=os.path.join(model_dir, "dict")
        ),
        num_threads=2
    )
)
tts_engine = sherpa_onnx.OfflineTts(cfg)
num_speakers = tts_engine.num_speakers

print(f"Scanning {num_speakers} speakers...")

def estimate_pitch_raw(samples, framerate):
    min_lag = int(framerate / 300)
    max_lag = int(framerate / 50)
    frame_size = 1024
    hop_size = 512
    pitches = []
    
    for i in range(0, len(samples) - frame_size, hop_size):
        frame = samples[i : i + frame_size]
        if np.max(np.abs(frame)) < 0.01:
            continue
            
        corr = np.correlate(frame, frame, mode='full')
        corr = corr[len(corr)//2:]
        r_range = corr[min_lag:max_lag]
        if len(r_range) == 0:
            continue
        peak_lag = np.argmax(r_range) + min_lag
        pitch = framerate / peak_lag
        pitches.append(pitch)
        
    if not pitches:
        return 0.0
    return float(np.median(pitches))

male_speakers = []
female_speakers = []

for sid in range(num_speakers):
    try:
        audio = tts_engine.generate("Hello, this is a pitch test for speaker ID.", sid=sid)
        samples = np.array(audio.samples, dtype=np.float32)
        pitch = estimate_pitch_raw(samples, audio.sample_rate)
        
        info = {"sid": sid, "pitch": pitch}
        if pitch > 0:
            if pitch < 165:
                male_speakers.append(info)
            else:
                female_speakers.append(info)
    except Exception as e:
        pass

print("\n--- MALE SPEAKERS (PITCH < 165 Hz) ---")
for s in sorted(male_speakers, key=lambda x: x['pitch']):
    print(f"ID {s['sid']}: Pitch = {s['pitch']:.1f} Hz")

print("\n--- FEMALE SPEAKERS (PITCH >= 165 Hz) ---")
for s in sorted(female_speakers, key=lambda x: x['pitch']):
    print(f"ID {s['sid']}: Pitch = {s['pitch']:.1f} Hz")
