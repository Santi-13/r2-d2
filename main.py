# main.py
import queue
import time
import sys
import numpy as np
import sounddevice as sd

# Importamos nuestros módulos
import config
import brain
import mouth
import ears

# Estado Global
q = queue.Queue()
audio_buffer = np.zeros((0, 1), dtype=np.float32)
is_recording = False
silence_start = None
last_interaction = time.time()
conversation_history = []

def callback(indata, frames, time, status):
    if status: print(status, file=sys.stderr)
    q.put(indata.copy())

def main():
    global is_recording, silence_start, audio_buffer, last_interaction, conversation_history    
    
    print("-----------------------------------")
    print("   R2-D2 HYBRID SYSTEM ONLINE")
    print("-----------------------------------")

    # 1. Cargar Oídos
    whisper = ears.load_model()
    #noise_threshold = 0.005 # O llamar a ears.calibrate()
    noise_threshold = ears.calibrate(q, 2, callback)
    
    # 2. Confirmación de Inicio
    mouth.speak("Sistemas híbridos en línea.")
    last_interaction = time.time()

    # 3. Bucle Principal
    with sd.InputStream(samplerate=config.SAMPLE_RATE, channels=1, callback=callback, blocksize=config.BLOCK_SIZE):
        print("\n🎤 Escuchando...")
        
        while True:
            # --- IDLE CHECK ---
            if not is_recording and (time.time() - last_interaction > config.IDLE_TIMEOUT):
                mouth.play_idle() 
                last_interaction = time.time()

            # --- PROCESAMIENTO DE AUDIO ---
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

                    if time.time() - silence_start > config.SILENCE_DURATION:
                        print("   --> 🛑 Procesando...")
                        
                        # A. Transcribir
                        segments, _ = whisper.transcribe(audio_buffer.flatten(), beam_size=5, language="es")
                        user_msg = " ".join([s.text for s in segments]).strip()

                        if len(user_msg) > 2:
                            print(f"\n🗣️  USER: {user_msg}")

                            # B. Pensar (Híbrido: Nube -> Local)
                            # --- PASO 1: AGREGAR USUARIO A MEMORIA ---
                            conversation_history.append({"role": "user", "content": user_msg})
                            
                            # --- PASO 2: RECORTAR MEMORIA (Ventana Deslizante) ---
                            # Si superamos el límite, borramos el más antiguo (índice 0)
                            if len(conversation_history) > config.MAX_MEMORY_TURNS:
                                conversation_history.pop(0)

                            # --- PASO 3: CONSULTAR CEREBRO (Pasamos la lista, no el string) ---
                            ai_reply = brain.query_hybrid(conversation_history)
                            
                            # C. Actuar
                            if "[DESCONOCIDO]" in ai_reply:
                                mouth.handle_confusion()
                                conversation_history.append({"role": "assistant", "content": "No entendí eso."})
                            else:
                                print(f"🤖 AI: {ai_reply}")
                                mouth.speak(ai_reply)
                                conversation_history.append({"role": "assistant", "content": ai_reply})

                        if len(conversation_history) > config.MAX_MEMORY_TURNS:
                            conversation_history.pop(0)

                        print("   (Limpiando buffer de audio...)")
                        with q.mutex:
                            q.queue.clear()  # <--- Borra todo lo que escuchó mientras hablaba
                        audio_buffer = np.zeros((0, 1), dtype=np.float32) # Reinicia el buffer de Whisper
                        
                        # Reset final
                        is_recording = False
                        silence_start = None
                        last_interaction = time.time()
                        print("\n🎤 Escuchando...")

            
            time.sleep(0.01)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApagando...")