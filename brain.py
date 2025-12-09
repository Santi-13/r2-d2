# brain.py
import requests
from openai import OpenAI
import config

# Inicializar cliente OpenAI (si hay key)
client = None
if config.OPENAI_KEY:
    client = OpenAI(api_key=config.OPENAI_KEY)

def query_hybrid(conversation_history):
    """
    Intenta usar la Nube (OpenAI). Si falla, usa Local (Ollama).
    Recibe una LISTA de mensajes: 
    [{"role": "user", "content": "Hola"}, {"role": "assistant", "content": "Bip bop..."}]
    """

    # 1. INTENTO: NUBE (OPENAI)
    if client:
        try:
            print("   ... ☁️  Consultando Nube (OpenAI)...")
            # Preparamos el mensaje de sistema
            system_msg = {"role": "system", "content": config.SYSTEM_PROMPT}
            full_messages = [system_msg] + conversation_history
            
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=full_messages,
                max_tokens=60,
                timeout=5
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"   ⚠️  Fallo de Nube. Cambiando a Local... ({e})")
    
    # 2. INTENTO: LOCAL (OLLAMA)
    # Si no hay cliente o falló el try anterior, llegamos aquí.
    return query_ollama_raw(conversation_history)

def format_history_for_llama(history):
    """
    Convierte la lista de diccionarios en un solo string de texto
    que Llama 3.2 puede entender perfectamente.
    """
    # 1. Empezamos con el System Prompt
    prompt_text = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{config.SYSTEM_PROMPT}<|eot_id|>"
    
    # 2. Añadimos el historial de conversación
    for msg in history:
        role = msg["role"] # "user" o "assistant"
        content = msg["content"]
        prompt_text += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
    
    # 3. Preparamos el turno del asistente (para que complete)
    prompt_text += "<|start_header_id|>assistant<|end_header_id|>\n\n"
    
    return prompt_text

def query_ollama_raw(history):
    print("   ... 🏠 Consultando Local (Serializado)...")
    
    # Convertimos la lista a un String gigante
    final_prompt = format_history_for_llama(history)
    
    # Volvemos al endpoint /api/generate (que sabemos que funciona)
    url = "http://localhost:11434/api/generate"
    
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": final_prompt,  
        "stream": False,
        "options": {
            "temperature": 0.3,
            "stop": ["<|eot_id|>"] # Le decimos cuándo dejar de hablar
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        
        print(f"DEBUG RESPONSE: {final_prompt}")

        response_json = response.json()
        
        text = response_json.get("response", "").strip()
        
        if not text:
            return "[Error: Respuesta vacía del modelo]"
            
        return text
        
    except Exception as e:
        return f"Error de conexión local: {e}"