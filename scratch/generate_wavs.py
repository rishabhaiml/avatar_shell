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
print(f"Num speakers: {tts_engine.num_speakers}")

os.makedirs("scratch/voices", exist_ok=True)

# Generate a small audio clip for speakers 0 to 10 to hear which one is Adam
test_text = "This is speaker number {} testing."
for sid in range(11):
    try:
        print(f"Generating for speaker {sid}...")
        audio = tts_engine.generate(test_text.format(sid), sid=sid)
        samples = np.array(audio.samples, dtype=np.float32)
        samples_i16 = (samples * 32767).astype(np.int16)
        
        wav_path = f"scratch/voices/speaker_{sid}.wav"
        with wave.open(wav_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(audio.sample_rate)
            wav_file.writeframes(samples_i16.tobytes())
        print(f"Saved {wav_path}")
    except Exception as e:
        print(f"Failed for speaker {sid}: {e}")
