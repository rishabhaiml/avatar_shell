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
