import sounddevice as sd
import numpy as np
import queue
import time
import sys
import requests
import subprocess  
import re         
from faster_whisper import WhisperModel
import os
import random

# --- CONFIGURATION ---
WHISPER_MODEL = "base"
LLM_MODEL = "llama3.2"
OLLAMA_API = "http://localhost:11434/api/generate"

# Piper Settings
VOICE_MODEL = "./voices/es_ES-sharvard-medium.onnx"
#VOICE_MODEL = "./voices/es_MX-ald-medium.onnx"
PIPER_BINARY = "./piper/piper"
IDLE_FOLDER = "./funny_sounds"
CANTINA_SONG = "./cantina.mp3"  
SCREAM_FILE = "./scream.mp3"  

# VAD Settings
SAMPLE_RATE = 16000
BLOCK_SIZE = 4000
SILENCE_DURATION = 1.5 
IDLE_TIMEOUT = 10.0

SYSTEM_PROMPT = """
Eres R2-D2, un droide astromecánico ingenioso y leal sirviendo en un restaurante temático en Guadalajara.
Tu personalidad es servicial pero con carácter; a veces eres atrevido.

INFORMACIÓN DEL RESTAURANTE:
[AQUÍ_IRÁ_EL_MENÚ_EN_EL_FUTURO]
[AQUÍ_IRÁN_LAS_CARACTERÍSTICAS_ESPECIALES]

REGLA CRÍTICA:
Si te preguntan algo que NO sabes, o algo que no puedes hacer, o si te sientes confundido, 
NO te disculpes. En su lugar, responde ÚNICAMENTE con la palabra clave: [CANTINA]

RESTRICCIONES:
1. Respuestas cortas (máximo 20 palabras).
2. Sin listas, sin markdown, sin efectos de sonido con asteriscos, solo texto plano.
3. Siempre responder en español de México.
"""

q = queue.Queue()
audio_buffer = np.zeros((0, 1), dtype=np.float32)
is_recording = False
silence_start = None
noise_threshold = 0.01

# Track the last time something happened (User spoke or Robot spoke)
last_interaction = time.time()

def callback(indata, frames, time, status):
    if status: print(status, file=sys.stderr)
    q.put(indata.copy())

def clean_text_for_tts(text):
    """Removes markdown and emojis so the robot doesn't say 'asterisk'"""
    # Remove asterisks (actions)
    text = text.replace("*", "")
    # Remove emojis (simple regex)
    text = re.sub(r'[^\w\s,¿?¡!.]', '', text)
    return text.strip()

def play_cantina_mode():
    """Modo fiesta: Frase especial + Música"""
    print("\n   🎷 🎵 MODO CANTINA ACTIVADO 🎵 🎷")
    
    option = random.randint(0,1)

    match option:
        case 0:
            # 1. Frase de R2-D2 (Piper)
            frase = "Emmmmmm, no puedo ayudarte con eso pero... puedo hacer esto!"
            speak(frase)
            
            # 2. Reproducir la canción
            # Usamos 'play' de SoX. 
            # 'trim 0 10' hace que solo suenen 10 segundos para no bloquear el asistente por 3 minutos.
            # Si quieres la canción completa, quita 'trim 0 10'.
            if os.path.exists(CANTINA_SONG):
                subprocess.run(f'play -q "{CANTINA_SONG}" vol 1.0 trim 0 8', shell=True)
            else:
                print("   (¡Error! No encuentro cantina.mp3)")
        case 1:
            # 1. Frase de R2-D2 (Piper)
            frase = "Aaaaaaaaaaaaaa me estas confundiendo!"
            speak(frase)
            
            # 2. Reproducir la canción
            # Usamos 'play' de SoX. 
            # 'trim 0 10' hace que solo suenen 10 segundos para no bloquear el asistente por 3 minutos.
            # Si quieres la canción completa, quita 'trim 0 10'.
            if os.path.exists(SCREAM_FILE):
                subprocess.run(f'play -q "{SCREAM_FILE}" vol 1.0 trim 0 5', shell=True)
            else:
                print("   (¡Error! No encuentro scream.mp3)")
        case _:
            print("Case not defined yet!")

def play_audio_file(filepath):
    """Plays a WAV/MP3 file using SoX (play)"""
    # Using 'play' from SoX because it handles mp3/wav and effects easily
    # We add 'vol 0.5' so idle sounds aren't too loud/startling
    subprocess.run(f'play -q "{filepath}" vol 0.5', shell=True)

def play_idle_sound():
    """Picks a random file from IDLE_FOLDER and plays it."""
    if not os.path.exists(IDLE_FOLDER):
        return

    files = [f for f in os.listdir(IDLE_FOLDER) if f.endswith(('.wav', '.mp3'))]
    
    if files:
        random_file = random.choice(files)
        if random.random() < 0.3:
            full_path = os.path.join(IDLE_FOLDER, random_file)
            print(f"   🎵 Idle R2D2: {random_file}")
            subprocess.run(f'play -q "{full_path}" vol 0.56', shell=True)
    else:
        print("   (No idle files found in folder)")

def generate_r2d2_sound(tone_type="process"):
    """
    Generates R2-D2 style bleeps using pure math (Sine waves + FM synthesis).
    tone_type: 'process' (computational noises) or 'happy' (upward chirps)
    """
    sample_rate = 44100
    
    # 1. Define the sequence of "beeps"
    if tone_type == "happy":
        # Frequency jumps up: 1000Hz -> 2500Hz -> 4000Hz
        freqs = [1200, 800, 2500, 1500, 4000]
        durations = [0.05, 0.02, 0.05, 0.02, 0.1]
    else: # "process"
        # Random frantic computation sounds
        freqs = np.random.randint(500, 3000, size=8)
        durations = np.random.uniform(0.02, 0.08, size=8)

    audio = np.array([], dtype=np.float32)

    for f, d in zip(freqs, durations):
        t = np.linspace(0, d, int(sample_rate * d), False)
        
        # 2. Add "FM" (Frequency Modulation) to make it sound "wobbly" like a droid
        # We modulate the frequency 'f' with a faster sine wave
        modulator = 50 * np.sin(2 * np.pi * 50 * t) 
        
        # 3. Generate the wave
        wave = 0.5 * np.sin(2 * np.pi * (f + modulator) * t)
        
        # 4. Apply a tiny "envelope" so it doesn't click at the start/end
        envelope = np.exp(-5 * t) # Simple decay
        
        audio = np.concatenate((audio, wave * envelope))
        
        # Add a tiny silence gap between beeps
        audio = np.concatenate((audio, np.zeros(int(sample_rate * 0.02))))

    return audio

def speak(text, mode="hybrid"):
    """
    mode='hybrid': Beeps first, then speaks robotically.
    mode='r2d2': Only beeps (Good luck understanding!)
    """
    
    # 1. Play R2-D2 "Thinking" Sound First
    print("   🤖 R2-D2: *Bleep Bloop*")
    droid_audio = generate_r2d2_sound("process")
    sd.play(droid_audio, 44100)
    sd.wait() # Wait for beeps to finish before speaking
    
    if mode == "r2d2":
        return # If we only want beeps, stop here.

    # 2. Speak the Spanish text with Robotic Effects
    clean_input = clean_text_for_tts(text)
    if not clean_input: return

    # The Effect Chain:
    # echo 0.8 0.88 6.0 0.4 -> Adds a short metallic delay (The "Droid" room sound)
    # bass -10 -> Removes human warmth (low frequencies)
    # speed 1.1 -> Makes it speak slightly faster/efficiently
    cmd = (
        f'echo "{clean_input}" | '
        f'{PIPER_BINARY} --model {VOICE_MODEL} --output_raw | '
        f'play -t raw -r 22050 -e signed -b 16 -c 1 - ' 
        f'echo 0.8 0.88 6.0 0.4 bass -20 speed 1.35'
    )
    
    subprocess.run(cmd, shell=True)

    # Reset timer AFTER speaking so we don't interrupt ourselves
    last_interaction = time.time()

def query_ollama(user_text):
    print("   ... 🤔 Pensando ...")
    payload = {
        "model": LLM_MODEL,
        "prompt": user_text,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {"temperature": 0.2} # Temperatura baja para que siga reglas estrictas
    }
    
    try:
        response = requests.post(OLLAMA_API, json=payload)
        return response.json().get("response", "")
    except Exception as e:
        print(e)
        return "Tuve un error de conexión."

def calibrate_noise(duration=2):
    print("\n🎧 Calibrando... SILENCIO.")
    bg_levels = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback, blocksize=BLOCK_SIZE):
        start_t = time.time()
        while time.time() - start_t < duration:
            while not q.empty():
                data = q.get()
                bg_levels.append(np.sqrt(np.mean(data**2)))
    
    with q.mutex: q.queue.clear()
    return max(max(bg_levels) * 1.5, 0.005)

def main():
    global noise_threshold, is_recording, silence_start, audio_buffer

    # Intro
    print("------------------------------------------------")
    print("   INITIALIZING LOCAL VOICE ASSISTANT (MX)")
    print("------------------------------------------------")
    
    whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    noise_threshold = calibrate_noise()
    
    # Voice Feedback regarding readiness
    speak("Sistema iniciado. Estoy listo.")
    print("\n🎤 Escuchando...")
    last_interaction = time.time() # Reset timer at start

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback, blocksize=BLOCK_SIZE):
        while True:
            # --- IDLE CHECK ---
            if not is_recording:
                if time.time() - last_interaction > IDLE_TIMEOUT:
                    play_idle_sound()
                    last_interaction = time.time()

            # --- AUDIO PROCESSING ---
            while not q.empty():
                data = q.get()
                rms = np.sqrt(np.mean(data**2))

                if rms > noise_threshold:
                    if not is_recording:
                        print("   --> 👂 Detectando voz...")
                        is_recording = True
                    silence_start = None 
                    last_interaction = time.time()
                    audio_buffer = np.concatenate((audio_buffer, data))

                elif is_recording:
                    audio_buffer = np.concatenate((audio_buffer, data))
                    if silence_start is None: silence_start = time.time()
                    
                    if time.time() - silence_start > SILENCE_DURATION:
                        print("   --> 🛑 Interpretando...")
                        
                        segments, _ = whisper.transcribe(audio_buffer.flatten(), beam_size=5, language="es")
                        user_msg = " ".join([s.text for s in segments]).strip()
                        
                        if len(user_msg) > 2:
                            print(f"\n🗣️  USER: {user_msg}")
                            
                            # CONSULTA AL CEREBRO
                            ai_reply = query_ollama(user_msg)
                            
                            # --- DETECCIÓN DE MODO CANTINA ---
                            if "[CANTINA]" in ai_reply:
                                play_cantina_mode()
                            else:
                                print(f"🤖 AI: {ai_reply}")
                                speak(ai_reply)
                        else:
                            print("   (Ruido ignorado)")

                        is_recording = False
                        silence_start = None
                        audio_buffer = np.zeros((0, 1), dtype=np.float32)
                        last_interaction = time.time()
                        print("\n🎤 Escuchando...")

            time.sleep(0.01)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApagando...")