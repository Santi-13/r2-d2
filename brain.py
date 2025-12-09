# brain.py
import requests
from openai import OpenAI
import config

# Inicializar cliente OpenAI (si hay key)
client = None
if config.OPENAI_KEY:
    client = OpenAI(api_key=config.OPENAI_KEY)

def query_hybrid(user_text):
    """
    Intenta usar la Nube (OpenAI). Si falla, usa Local (Ollama).
    """
    
    # 1. INTENTO: NUBE (OPENAI)
    if client:
        try:
            print("   ... ☁️  Consultando Nube (OpenAI)...")
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": config.SYSTEM_PROMPT},
                    {"role": "user", "content": user_text}
                ],
                max_tokens=60,
                timeout=5 # Si tarda más de 5s, abortar y usar local
            )
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"   ⚠️  Fallo de Nube ({e}). Cambiando a Local...")
    
    # 2. INTENTO: LOCAL (OLLAMA)
    # Si no hay cliente o falló el try anterior, llegamos aquí.
    return query_ollama(user_text)

def query_ollama(user_text):
    print("   ... 🏠 Consultando Local (Llama 3.2)...")
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": user_text,
        "system": config.SYSTEM_PROMPT,
        "stream": False,
        "options": {"temperature": 0.25} 
    }
    
    try:
        response = requests.post(url, json=payload)
        return response.json().get("response", "")
    except Exception as e:
        return f"Error crítico de sistemas: {e}"