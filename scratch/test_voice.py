import os
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

# Let's see if generate accepts sid as a string or integer
try:
    audio = tts_engine.generate("Hello world", sid="am_adam")
    print("Success with sid='am_adam'")
except Exception as e:
    print(f"Failed with sid='am_adam': {e}")

try:
    audio = tts_engine.generate("Hello world", sid=4)
    print("Success with sid=4")
except Exception as e:
    print(f"Failed with sid=4: {e}")

# Let's inspect the OfflineTts class properties and methods
print(dir(tts_engine))
