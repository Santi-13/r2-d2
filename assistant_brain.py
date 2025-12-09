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

# --- 1. CONFIGURACIÓN DEL SISTEMA ---
WHISPER_MODEL = "base"
LLM_MODEL = "llama3.2"
OLLAMA_API = "http://localhost:11434/api/generate"

# Configuración de Voz y Audio
PIPER_BINARY = "./piper/piper"
VOICE_MODEL = "./voices/es_ES-sharvard-medium.onnx"

# Rutas de Carpetas
IDLE_FOLDER = "./funny_sounds"

# --- 2. DICCIONARIO DE EASTER EGGS (NUEVO) ---
# Aquí puedes agregar todos los sonidos especiales que quieras.
# Estructura: "nombre_clave": "ruta_del_archivo"
SPECIAL_SOUNDS = {
    "cantina": "./cantina.mp3",
    "scream": "./scream.mp3",
    "sad": "./sad_trombone.mp3", # Ejemplo: puedes agregar este archivo si quieres
    "vader": "./imperial_march.mp3" # Ejemplo
}

# --- 3. LISTA DE RESPUESTAS INGENIOSAS (COMEBACKS) ---
# Cuando R2 no sepa qué decir, elegirá una de estas al azar.
R2_SASSY_RESPONSES = [
    "Mis bancos de memoria no tienen datos sobre eso, y honestamente, no me importa.",
    "Soy un droide astromecánico, no una enciclopedia con patas.",
    "Bip bip. Eso suena a problema de humanos, no mío.",
    "¿En serio me preguntas eso a mí? Pregúntale al mesero.",
    "Procesando... Procesando... Error. Pregunta aburrida detectada.",
    "Mira, si no tiene tuercas o hiperpropulsores, no sé de qué me hablas.",
    "Mejor pídete unos tacos y olvida esa pregunta.",
    "Ahorita no joven, estoy calibrando mis sensores.",
    "Esa información está clasificada por el Imperio.",
    "No tengo idea, pero seguro C 3 P O te echaría un rollo de tres horas sobre eso."
]

# Configuración VAD (Detección de voz)
SAMPLE_RATE = 16000
BLOCK_SIZE = 4000
SILENCE_DURATION = 1.5 
IDLE_TIMEOUT = 10.0

# --- 4. SYSTEM PROMPT ACTUALIZADO ---
SYSTEM_PROMPT = """
Eres R2-D2, un droide astromecánico ingenioso y leal sirviendo en un restaurante temático en Guadalajara.
Tu personalidad es servicial pero con mucho carácter; eres atrevido y usas jerga mexicana ligera.

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

# Variables Globales de Estado
q = queue.Queue()
audio_buffer = np.zeros((0, 1), dtype=np.float32)
is_recording = False
silence_start = None
noise_threshold = 0.01
last_interaction = time.time()

def callback(indata, frames, time, status):
    if status: print(status, file=sys.stderr)
    q.put(indata.copy())

def clean_text_for_tts(text):
    text = text.replace("*", "")
    text = re.sub(r'[^\w\s,¿?¡!.]', '', text)
    return text.strip()

# --- 5. NUEVA FUNCIÓN MAESTRA DE EVENTOS ---
def trigger_confusion_event():
    """
    Decide qué hacer cuando la IA no sabe la respuesta.
    Usa probabilidades para no ser repetitivo.
    """
    print("\n   🎲 R2-D2 está confundido... Tirando dados de comportamiento.")
    
    # Generamos un número entre 0.0 y 1.0
    roll = random.random()

    if roll < 0.70:
        # 70% de probabilidad: Respuesta Sarcástica (Comeback)
        frase = random.choice(R2_SASSY_RESPONSES)
        speak(frase)

    elif roll < 0.85:
        # 15% de probabilidad: MODO CANTINA
        print("   🎷 ¡Fiesta!")
        speak("Emmmmmm, no sé como ayudarte, pero ¡puedo hacer esto!")
        play_special_sound("cantina", volume=1.0, duration=8)

    else:
        # 15% de probabilidad: MODO PÁNICO
        print("   😱 ¡Pánico!")
        speak("¡Error de sistema! ¡Sobrecarga!")
        play_special_sound("scream", volume=0.8, duration=4)

def play_special_sound(sound_key, volume=0.5, duration=None):
    """Reproduce un sonido del diccionario SPECIAL_SOUNDS"""
    if sound_key not in SPECIAL_SOUNDS:
        print(f"   (Audio {sound_key} no configurado)")
        return

    filepath = SPECIAL_SOUNDS[sound_key]
    
    if os.path.exists(filepath):
        # Construimos el comando de SoX
        cmd = f'play -q "{filepath}" vol {volume}'
        if duration:
            cmd += f' trim 0 {duration}'
        
        subprocess.run(cmd, shell=True)
    else:
        print(f"   (Archivo no encontrado: {filepath})")

def play_idle_sound():
    """Sonidos aleatorios de fondo (chiflidos, beeps)"""
    if not os.path.exists(IDLE_FOLDER): return

    files = [f for f in os.listdir(IDLE_FOLDER) if f.endswith(('.wav', '.mp3'))]
    if files:
        random_file = random.choice(files)
        # 40% de probabilidad de sonar para no ser molesto
        if random.random() < 0.4:
            full_path = os.path.join(IDLE_FOLDER, random_file)
            print(f"   🎵 Idle R2D2: {random_file}")
            subprocess.run(f'play -q "{full_path}" vol 0.4', shell=True)

def generate_r2d2_sound(tone_type="process"):
    """Generación matemática de beeps (sin archivos)"""
    sample_rate = 44100
    if tone_type == "happy":
        freqs = [1200, 800, 2500, 1500, 4000]
        durations = [0.05, 0.02, 0.05, 0.02, 0.1]
    else: 
        freqs = np.random.randint(500, 3000, size=8)
        durations = np.random.uniform(0.02, 0.08, size=8)

    audio = np.array([], dtype=np.float32)
    for f, d in zip(freqs, durations):
        t = np.linspace(0, d, int(sample_rate * d), False)
        modulator = 50 * np.sin(2 * np.pi * 50 * t) 
        wave = 0.5 * np.sin(2 * np.pi * (f + modulator) * t)
        envelope = np.exp(-5 * t)
        audio = np.concatenate((audio, wave * envelope))
        audio = np.concatenate((audio, np.zeros(int(sample_rate * 0.02))))
    return audio

def speak(text, mode="hybrid"):
    # 1. Beeps de pensamiento
    print("   🤖 R2-D2: *Bleep Bloop*")
    droid_audio = generate_r2d2_sound("process")
    sd.play(droid_audio, 44100)
    sd.wait()
    
    if mode == "r2d2": return

    # 2. Voz TTS
    clean_input = clean_text_for_tts(text)
    if not clean_input: return

    # Efectos SoX: Pitch, Echo, Bass
    cmd = (
        f'echo "{clean_input}" | '
        f'{PIPER_BINARY} --model {VOICE_MODEL} --output_raw | '
        f'play -t raw -r 22050 -e signed -b 16 -c 1 - ' 
        f'echo 0.4 0.88 6.0 0.4 bass -30 speed 1.3'
    )
    subprocess.run(cmd, shell=True)
    
    # Reiniciar timer de inactividad
    global last_interaction
    last_interaction = time.time()

def query_ollama(user_text):
    print("   ... 🤔 Pensando ...")
    payload = {
        "model": LLM_MODEL,
        "prompt": user_text,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {"temperature": 0.2} 
    }
    try:
        response = requests.post(OLLAMA_API, json=payload)
        return response.json().get("response", "")
    except Exception as e:
        print(e)
        return "Error crítico en el núcleo."

def calibrate_noise(duration=2):
    print("\n🎧 Calibrando entorno... SILENCIO.")
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
    global noise_threshold, is_recording, silence_start, audio_buffer, last_interaction

    print("------------------------------------------------")
    print("   R2-D2 SYSTEM: GUADALAJARA MODE ONLINE")
    print("------------------------------------------------")
    
    whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    noise_threshold = calibrate_noise()
    
    speak("Sistemas operativos. Esperando comandos.")
    print("\n🎤 Escuchando...")
    last_interaction = time.time()

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
                        print("   --> 🛑 Procesando...")
                        
                        segments, _ = whisper.transcribe(audio_buffer.flatten(), beam_size=5, language="es")
                        user_msg = " ".join([s.text for s in segments]).strip()
                        
                        if len(user_msg) > 2:
                            print(f"\n🗣️  USER: {user_msg}")
                            
                            ai_reply = query_ollama(user_msg)
                            
                            # --- LÓGICA DE RESPUESTA INTELIGENTE ---
                            # Buscamos la etiqueta [DESCONOCIDO] en la respuesta de la IA
                            if "[DESCONOCIDO]" in ai_reply:
                                trigger_confusion_event()
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