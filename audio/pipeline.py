import time
import queue
import numpy as np
import sounddevice as sd
import config


def audio_hardware_capture_loop():
    """
    Background thread: streams microphone frames into AUDIO_FRAME_QUEUE via a
    non-blocking sounddevice InputStream.  Single-codepath — no PyAudio fallback.
    """
    def _callback(indata, frames, callback_time, status):
        # status carries under/overflow flags; we pass silently to avoid log spam
        config.AUDIO_FRAME_QUEUE.put(indata.copy().tobytes())

    print("mic: Opening cross-platform CFFI capture stream via sounddevice...")

    while True:
        try:
            with sd.InputStream(
                samplerate=config.SAMPLE_RATE,
                blocksize=config.CHUNK,
                device=None,        # Fallback to system-default audio interface
                channels=1,
                dtype='int16',
                callback=_callback,
            ):
                while True:
                    time.sleep(0.1)
        except Exception as e:
            print(f"⚠️ sounddevice capture error ({e}). Retrying in 1s...")
            time.sleep(1.0)


def playback_worker_thread(flush_callback=None):
    """
    Background thread: drains SPEECH_PLAYBACK_QUEUE and writes PCM frames to the
    default output device via sounddevice OutputStream.  Dispatches real-time lip-
    sync viseme metrics over the WebSocket callback on every chunk.
    """
    speaker_stream = None
    print("speaker: Opening cross-platform CFFI playback stream via sounddevice...")

    try:
        speaker_stream = sd.OutputStream(
            samplerate=24000,   # Matches Kokoro TTS output rate
            channels=1,
            dtype='int16',
            blocksize=512,
        )
        speaker_stream.start()
    except Exception as e:
        print(f"❌ Failed to open sounddevice output stream: {e}")

    print("speaker: Background playback channel successfully initialized.")

    smoothing = 0.5
    current_aa = current_ee = current_ih = current_oh = current_ou = 0.0

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

            while current_frame < total_frames:
                if config.INTERRUPT_FLAG.is_set():
                    print("🛑 Playback interrupted!")
                    break

                end_frame = min(current_frame + chunk_size, total_frames)
                audio_array = audio_np[current_frame:end_frame]

                # Real-time intensity → viseme mapping
                vol = float(np.sqrt(np.mean(audio_array.astype(np.float32) ** 2)))
                if vol < 150:
                    target = {'aa': 0.0, 'ee': 0.0, 'ih': 0.0, 'oh': 0.0, 'ou': 0.0}
                else:
                    nv = min(1.0, vol / 5000.0)
                    target = {
                        'aa': nv * 0.7,
                        'ee': nv * 0.3,
                        'ih': nv * 0.2,
                        'oh': nv * 0.5,
                        'ou': nv * 0.4,
                    }

                current_aa += (target['aa'] - current_aa) * smoothing
                current_ee += (target['ee'] - current_ee) * smoothing
                current_ih += (target['ih'] - current_ih) * smoothing
                current_oh += (target['oh'] - current_oh) * smoothing
                current_ou += (target['ou'] - current_ou) * smoothing

                if config.SEND_UI_STATE_CALLBACK:
                    config.SEND_UI_STATE_CALLBACK(
                        current_aa, current_ee, current_ih,
                        current_oh, current_ou, listening=False
                    )

                if speaker_stream:
                    speaker_stream.write(audio_array)

                current_frame += chunk_size

            # Send silent mouth viseme at end of sentence
            if config.SEND_UI_STATE_CALLBACK:
                config.SEND_UI_STATE_CALLBACK(0.0, 0.0, 0.0, 0.0, 0.0, listening=False)

        except queue.Empty:
            config.SPEAKER_ACTIVE = False
            config.SPEECH_IN_PROGRESS = False

        except Exception as e:
            print(f"❌ Playback Worker Exception: {e}")
            time.sleep(0.1)

    # Graceful stream cleanup on sentinel None
    try:
        if speaker_stream:
            speaker_stream.stop()
            speaker_stream.close()
    except Exception:
        pass
