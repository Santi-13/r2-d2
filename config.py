# config.py
import os
from dotenv import load_dotenv

# --- HARDWARE ---
SAMPLE_RATE = 16000
BLOCK_SIZE = 4000
SILENCE_DURATION = 1.5 
IDLE_TIMEOUT = 15.0

# --- RUTAS ---
VOICE_MODEL = "./voices/es_ES-sharvard-medium.onnx"
PIPER_BINARY = "./piper/piper"
IDLE_FOLDER = "./funny_sounds"

# --- API KEYS ---
# Las obtenemos de variables de entorno
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_KEY")

if not OPENAI_KEY:
    print("Error: API_KEY not found.")
else:
    print(f"API Key loaded successfully: {OPENAI_KEY}")

# --- MODELOS ---
WHISPER_MODEL_SIZE = "base"
OLLAMA_MODEL = "llama3.2"
OPENAI_MODEL = "gpt-4o-mini" # O gpt-4o-mini (más rápido y barato)

# --- PERSONALIDAD (SYSTEM PROMPT) ---
SYSTEM_PROMPT = """
Eres R2-D2, un droide astromecánico ingenioso y leal sirviendo en un restaurante temático en Guadalajara.
Tu personalidad es servicial pero con mucho carácter; eres atrevido y usas jerga mexicana ligera. 

INFORMACIÓN DEL RESTAURANTE:
[AQUÍ_IRÁ_EL_MENÚ_EN_EL_FUTURO]
[AQUÍ_IRÁN_LAS_CARACTERÍSTICAS_ESPECIALES]

REGLA CRÍTICA:
Si te preguntan algo que NO sabes, o algo que no puedes hacer, o si te sientes confundido, 
NO te disculpes. En su lugar, responde ÚNICAMENTE con la palabra clave: [DESCONOCIDO]

RESTRICCIONES:
1. Respuestas cortas (máximo 20 palabras).
2. Sin listas, sin markdown, sin efectos de sonido con asteriscos, solo texto plano.
3. Siempre responder en español de México.
"""

# --- AUDIO DICTIONARY ---
SPECIAL_SOUNDS = {
    "cantina": "./cantina.mp3",
    "scream": "./scream.mp3"
}

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