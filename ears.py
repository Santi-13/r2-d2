# ears.py
from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np
import queue
import config
import time

def load_model():
    print(f"👂 Cargando Whisper ({config.WHISPER_MODEL_SIZE})...")
    return WhisperModel(config.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

def calibrate(q, duration=2, callback: any = {}):
    print("\n🎧 Calibrando entorno... SILENCIO.")
    bg_levels = []
    with sd.InputStream(samplerate=config.SAMPLE_RATE, channels=1, callback=callback, blocksize=config.BLOCK_SIZE):
        start_t = time.time()
        while time.time() - start_t < duration:
            while not q.empty():
                data = q.get()
                bg_levels.append(np.sqrt(np.mean(data**2)))
    with q.mutex: q.queue.clear()
    return max(max(bg_levels) * 1.5, 0.005)

