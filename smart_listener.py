import sounddevice as sd
import numpy as np
import queue
import time
import sys
from faster_whisper import WhisperModel

# --- CONFIGURATION ---
MODEL_PATH = "base"     # Or your converted "my-spanish-model" path
SAMPLE_RATE = 16000     # Hz
BLOCK_SIZE = 4000       # Size of audio chunks (4000 = 0.25s)
SILENCE_DURATION = 1.5  # Seconds of silence to trigger "End of Sentence"

# Global Variables
q = queue.Queue()
audio_buffer = np.zeros((0, 1), dtype=np.float32)
is_recording = False    # State machine flag
silence_start = None    # Timer for silence
noise_threshold = 0.01  # Default (will be calibrated)

def callback(indata, frames, time, status):
    """Real-time Audio Input Callback"""
    if status:
        print(status, file=sys.stderr)
    q.put(indata.copy())

def calibrate_noise(duration=2):
    """
    Measures ambient room noise to set a dynamic threshold.
    """
    print("\n🎧 Calibrating background noise... PLEASE REMAIN SILENT.")
    bg_levels = []
    
    # We cheat and use the same stream/queue logic for a few seconds
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback, blocksize=BLOCK_SIZE):
        start_time = time.time()
        while time.time() - start_time < duration:
            while not q.empty():
                data = q.get()
                rms = np.sqrt(np.mean(data**2))
                bg_levels.append(rms)
    
    # Clear the queue for the real app
    with q.mutex:
        q.queue.clear()
        
    # Set threshold slightly above the maximum noise detected
    max_noise = max(bg_levels)
    new_threshold = max_noise * 1.5  # 50% safety margin
    # Ensure a bare minimum so we don't trigger on thermal noise
    new_threshold = max(new_threshold, 0.002) 
    
    print(f"✅ Calibration Complete.")
    print(f"   - Max Background Noise: {max_noise:.5f}")
    print(f"   - Trigger Threshold:    {new_threshold:.5f}")
    return new_threshold

def main():
    global noise_threshold, is_recording, silence_start, audio_buffer

    # 1. Load Model
    print(f"🧠 Loading {MODEL_PATH} model...")
    model = WhisperModel(MODEL_PATH, device="cpu", compute_type="int8")

    # 2. Calibrate
    noise_threshold = calibrate_noise()
    
    print("\n🎤 Assistant is Listening (Spanish)...")
    print(f"   (Speak to start. Stop speaking for {SILENCE_DURATION}s to process.)")

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback, blocksize=BLOCK_SIZE):
        while True:
            while not q.empty():
                data = q.get()
                
                # Calculate energy of this chunk
                rms = np.sqrt(np.mean(data**2))

                # --- STATE MACHINE LOGIC ---
                
                # CASE 1: We hear sound (User is talking)
                if rms > noise_threshold:
                    if not is_recording:
                        print("   --> 🗣️  Voice detected. Recording started...")
                        is_recording = True
                    
                    # Reset silence timer because we hear sound
                    silence_start = None 
                    
                    # Append data
                    audio_buffer = np.concatenate((audio_buffer, data))

                # CASE 2: We hear silence (User might be done)
                elif is_recording:
                    # Append data (we keep the silence so the audio doesn't sound chopped)
                    audio_buffer = np.concatenate((audio_buffer, data))
                    
                    if silence_start is None:
                        silence_start = time.time()
                    
                    # Check if silence has lasted long enough
                    if time.time() - silence_start > SILENCE_DURATION:
                        print("   --> 🛑 Silence detected. Processing...")
                        
                        # --- PROCESS THE AUDIO ---
                        # Transcribe the accumulated buffer
                        segments, _ = model.transcribe(
                            audio_buffer.flatten(), 
                            beam_size=5, 
                            language="es",
                            task="transcribe"
                        )
                        
                        # Print result
                        full_text = " ".join([s.text for s in segments]).strip()
                        if len(full_text) > 2: # Ignore tiny hallucinations
                            print(f"\n📝 User: {full_text}\n")
                            # [Here is where you will eventually call Ollama]
                        else:
                            print("   (Ignored empty audio)")

                        # Reset State
                        is_recording = False
                        silence_start = None
                        audio_buffer = np.zeros((0, 1), dtype=np.float32)
                        print("🎤 Listening...")

            time.sleep(0.01) # Yield CPU

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye!")