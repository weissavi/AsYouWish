
import uuid
from .config_loader import load_config, load_persona
from .context import render_prompt, update_history, get_initial_history
import requests

CONFIG = load_config()
AI_PERSONA = load_persona(CONFIG['persona_files']['ai'])
USER_PERSONA = load_persona(CONFIG['persona_files']['user'])

BASE_URL = CONFIG.get("base_url")
MODEL = CONFIG.get("default_model")
API_KEY = CONFIG.get("api_key")

def generate_fantasy(user_input: str, session_id: str) -> str:
    if not session_id:
        session_id = str(uuid.uuid4())

    history = get_initial_history(session_id, AI_PERSONA, USER_PERSONA)
    history = update_history(history, user_input)

    payload = {
        "model": MODEL,
        "messages": history,
        "temperature": 0.9,
        "max_tokens": 500
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(BASE_URL, headers=headers, json=payload)
    response_data = response.json()

    try:
        return response_data['choices'][0]['message']['content']
    except Exception as e:
        return f"[Error generating response: {e}]"
