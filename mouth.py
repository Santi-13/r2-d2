# mouth.py
import subprocess
import os
import random
import numpy as np
import sounddevice as sd
import re
import config
import limbs

def clean_text(text):
    text = text.replace("*", "")
    text = re.sub(r'[^\w\s,¿?¡!.]', '', text)
    return text.strip()

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

def play_file(filepath, vol=0.5, trim=None):
    if not os.path.exists(filepath): return
    cmd = f'play -q "{filepath}" vol {vol}'
    if trim: cmd += f' trim 0 {trim}'
    subprocess.run(cmd, shell=True)

def speak(text):
    # Beeps
    droid_audio = generate_r2d2_sound("process")
    sd.play(droid_audio, 44100)
    sd.wait()
    
    clean = clean_text(text)
    if not clean: return
    
    print(f"   🔊 R2: {clean}")

    # --- INICIO DE HABLA: Ojo parpadea ---
    limbs.controller.send_command("eye", "talk")
    
    # Generar comando de audio
    cmd = (
        f'echo "{clean}" | '
        f'{config.PIPER_BINARY} --model {config.VOICE_MODEL} --output_raw | '
        f'play -t raw -r 22050 -e signed -b 16 -c 1 - ' 
        f'echo 0.8 0.88 6.0 0.4 bass -20 speed 1.2'
    )
    
    # Reproducir (esto bloquea el hilo hasta que termine el audio)
    subprocess.run(cmd, shell=True)

    # --- FIN DE HABLA: Ojo rojo estático ---
    limbs.controller.send_command("eye", "silent")

def handle_confusion():
    """ 
    Maneja lo que hace el programa cuando R2-D2 
    no sabe que responder y envía [DESCONOCIDO]
    """
    print("   🎲 Evento de Confusión activado...")
    roll = random.random()
    
    if roll < 0.70:
        frase = random.choice(config.R2_SASSY_RESPONSES)
        speak(frase)
    elif roll < 0.85:
        speak("Emmmmmm, no sé como ayudarte, pero ¡puedo hacer esto!")
        play_file(config.SPECIAL_SOUNDS["cantina"], vol=1.0, trim=8)
    else:
        speak("¡Sobrecarga de sistemas!")
        play_file(config.SPECIAL_SOUNDS["scream"], vol=0.8, trim=4)

def play_idle():
    """Sonidos aleatorios de fondo (chiflidos, beeps)"""
    if not os.path.exists(config.IDLE_FOLDER): return

    files = [f for f in os.listdir(config.IDLE_FOLDER) if f.endswith(('.wav', '.mp3'))]
    if files:
        random_file = random.choice(files)
        # 40% de probabilidad de sonar para no ser molesto
        if random.random() < 0.4:
            full_path = os.path.join(config.IDLE_FOLDER, random_file)
            print(f"   🎵 Idle R2D2: {random_file}")
            subprocess.run(f'play -q "{full_path}" vol 0.4', shell=True)