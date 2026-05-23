import time
import queue
import numpy as np
import config
from audio.vad import calculate_frame_rms

try:
    import pyaudio
except ImportError:
    pyaudio = None

try:
    import sounddevice as sd
except ImportError:
    sd = None

def audio_hardware_capture_loop(pyaudio_instance):
    """
    Main thread running the physical soundcard input stream pipeline.
    """
    if pyaudio_instance is None:
        # Fallback to sounddevice for Windows/compile-free environments
        if sd is None:
            print("⚠️ No PyAudio or Sounddevice available. Microphone capture is disabled.")
            return

        def callback(indata, frames, time_info, status):
            config.AUDIO_FRAME_QUEUE.put(indata.copy().tobytes())

        print("mic: Opening thread-safe background capture channels via sounddevice...")
        try:
            with sd.InputStream(samplerate=config.RATE, channels=1, dtype='int16', blocksize=config.CHUNK, callback=callback):
                while True:
                    time.sleep(0.1)
        except Exception as e:
            print(f"⚠️ Soundcard hardware record drop (sounddevice): {e}")
            time.sleep(0.5)
            # Retry loop in case soundcard was busy
            while True:
                try:
                    with sd.InputStream(samplerate=config.RATE, channels=1, dtype='int16', blocksize=config.CHUNK, callback=callback):
                        while True:
                            time.sleep(0.1)
                except Exception:
                    time.sleep(1.0)
    else:
        # Standard PyAudio capture
        stream = pyaudio_instance.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=config.RATE,
            input=True,
            frames_per_buffer=config.CHUNK
        )
        
        print("mic: Opening thread-safe background capture channels...")
        
        while True:
            try:
                raw_bytes = stream.read(config.CHUNK, exception_on_overflow=False)
                config.AUDIO_FRAME_QUEUE.put(raw_bytes)
            except Exception as e:
                print(f"⚠️ Soundcard hardware record drop: {e}")
                time.sleep(0.01)

def playback_worker_thread(pyaudio_instance, flush_callback=None):
    """
    Main thread running the hardware speech output playback stream and real-time lip sync visemes.
    """
    speaker_stream = None
    if pyaudio_instance is None:
        # Fallback to sounddevice for Windows/compile-free environments
        if sd is None:
            print("⚠️ No PyAudio or Sounddevice available. Playout is disabled.")
            return
            
        print("speaker: Opening thread-safe background playback channels via sounddevice...")
        try:
            speaker_stream = sd.OutputStream(
                samplerate=24000,
                channels=1,
                dtype='int16',
                blocksize=512
            )
            speaker_stream.start()
        except Exception as e:
            print(f"❌ Failed to open sounddevice output stream: {e}")
    else:
        # Open speaker stream natively at 24000Hz (matching Kokoro output rate)
        speaker_stream = pyaudio_instance.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=24000,
            output=True,
            frames_per_buffer=512
        )
    
    print("speaker: Background playback channel successfully initialized.")
    
    while True:
        try:
            audio_bytes = config.SPEECH_PLAYBACK_QUEUE.get(timeout=0.05)
            if audio_bytes is None:
                break
                
            config.SPEAKER_ACTIVE = True
            config.SPEECH_IN_PROGRESS = True
            
            if config.INTERRUPT_FLAG.is_set():
                continue
            
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
            total_frames = len(audio_np)
            
            chunk_size = 512
            current_frame = 0
            current_aa, current_ee, current_ih, current_oh, current_ou = 0.0, 0.0, 0.0, 0.0, 0.0
            smoothing = 0.5
            
            while current_frame < total_frames:
                if config.INTERRUPT_FLAG.is_set():
                    print("🛑 Playback interrupted!")
                    break
                    
                end_frame = min(current_frame + chunk_size, total_frames)
                audio_array = audio_np[current_frame:end_frame]
                data = audio_array.tobytes()
                
                # Calculate real-time intensity visemes
                vol = float(np.sqrt(np.mean(np.square(audio_array.astype(np.float32)))))
                if vol < 150: 
                    target = {'aa': 0.0, 'ee': 0.0, 'ih': 0.0, 'oh': 0.0, 'ou': 0.0}
                else:
                    normalized_vol = min(1.0, vol / 5000.0)
                    target = {
                        'aa': normalized_vol * 0.7,
                        'ee': normalized_vol * 0.3,
                        'ih': normalized_vol * 0.2,
                        'oh': normalized_vol * 0.5,
                        'ou': normalized_vol * 0.4
                    }
                    
                current_aa += (target['aa'] - current_aa) * smoothing
                current_ee += (target['ee'] - current_ee) * smoothing
                current_ih += (target['ih'] - current_ih) * smoothing
                current_oh += (target['oh'] - current_oh) * smoothing
                current_ou += (target['ou'] - current_ou) * smoothing
                
                # Dispatch real-time visemes over the thread-safe websocket callback register
                if config.SEND_UI_STATE_CALLBACK:
                    config.SEND_UI_STATE_CALLBACK(current_aa, current_ee, current_ih, current_oh, current_ou, listening=False)
                    
                if pyaudio_instance is None:
                    if speaker_stream:
                        speaker_stream.write(audio_array)
                else:
                    speaker_stream.write(data)
                current_frame += chunk_size
            
            # Send silent mouth viseme state at end of sentence
            if config.SEND_UI_STATE_CALLBACK:
                config.SEND_UI_STATE_CALLBACK(0.0, 0.0, 0.0, 0.0, 0.0, listening=False)
                
        except queue.Empty:
            config.SPEAKER_ACTIVE = False
            config.SPEECH_IN_PROGRESS = False
            
        except Exception as e:
            print(f"❌ Playback Worker Exception: {e}")
            time.sleep(0.1)
            
    # Cleanup speaker stream explicitly
    try:
        if pyaudio_instance is None:
            if speaker_stream:
                speaker_stream.stop()
                speaker_stream.close()
        else:
            speaker_stream.stop_stream()
            speaker_stream.close()
    except Exception:
        pass
