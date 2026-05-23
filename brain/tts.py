import os
import time
import queue
import numpy as np
import sherpa_onnx
import config

def kokoro_synthesizer_worker():
    print("🧠 Initializing Native C++ Sherpa-ONNX Kokoro Engine...")
    
    # Establish absolute, forward-slash-safe path coordinates matching standard downloaded layout structures
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_dir = os.path.join(base_dir, "weights", "kokoro-v1.0")
    
    def to_safe_path(p):
        return os.path.abspath(p).replace("\\", "/")
        
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                model=to_safe_path(os.path.join(model_dir, "model.onnx")),
                voices=to_safe_path(os.path.join(model_dir, "voices.bin")),
                tokens=to_safe_path(os.path.join(model_dir, "tokens.txt")),
                data_dir=to_safe_path(os.path.join(model_dir, "espeak-ng-data")),
                lexicon=to_safe_path(os.path.join(model_dir, "lexicon-us-en.txt")),
                dict_dir=to_safe_path(os.path.join(model_dir, "dict"))
            ),
            num_threads=2
        )
    )
    
    # Instantiate the compiled native offline TTS engine
    tts_engine = sherpa_onnx.OfflineTts(cfg)
    
    # Target voice ID matching am_michael in this binary layout (ID 16, pitch 118.8 Hz)
    target_speaker_id = 16
    print("🚀 Native Kokoro Synthesis Worker Ready.")
    
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
            print(f"🎨 Kokoro Synthesizing: {sentence!r}")
            start_time = time.time()
            
            # Generate speech waveform natively via C++ bindings
            audio_generated = tts_engine.generate(
                text=sentence, 
                sid=target_speaker_id, 
                speed=1.0
            )
            
            samples_list = audio_generated.samples
            
            if samples_list and len(samples_list) > 0:
                # Safely convert plain Python list to optimized NumPy Float32 array
                samples_array = np.array(samples_list, dtype=np.float32)
                
                # Scale from normalized float space into 16-bit Mono PCM bytes
                audio_i16 = (samples_array * 32767).astype(np.int16).tobytes()
                
                elapsed = time.time() - start_time
                print(f"⏱️ Native Kokoro Synthesis took {elapsed:.2f}s for: {sentence!r}")
                
                # Hand over to PyAudio playback queue flawlessly
                config.SPEECH_PLAYBACK_QUEUE.put(audio_i16)
                
        except Exception as e:
            print(f"❌ Native synthesis error inside C-bindings pipeline: {e}")
        finally:
            config.SYNTHESIS_ACTIVE = False
            config.TTS_PROCESSING = False
