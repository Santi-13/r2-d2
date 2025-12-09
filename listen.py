from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np
import queue

# SETTINGS
MODEL_SIZE = "small" # "tiny" is instant, "base" is smarter. Start with tiny.
SAMPLE_RATE = 16000

q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(indata.copy())

print(f"Loading {MODEL_SIZE} model... (this takes 5s on first run)")
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
#model = WhisperModel("my-spanish-model", device="cpu", compute_type="int8")
print("Speak now! (Ctrl+C to stop)")

# Buffer to hold audio
audio_buffer = np.zeros((0, 1), dtype=np.float32)

with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback):
    while True:
        # Get data from queue
        while not q.empty():
            data = q.get()
            audio_buffer = np.concatenate((audio_buffer, data))
        
        # If we have 2 seconds of audio, try to transcribe
        if len(audio_buffer) > SAMPLE_RATE * 2:
            segments, _ = model.transcribe(audio_buffer.flatten(), beam_size=5)
            for segment in segments:
                print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
            
            # Reset buffer (Simplistic logic for testing)
            audio_buffer = np.zeros((0, 1), dtype=np.float32)