
from pathlib import Path
import json
from jinja2 import Template
import os

HISTORY_DIR = Path(__file__).parent.parent / "histories"
HISTORY_DIR.mkdir(exist_ok=True)

def render_prompt(template_path: str, context: dict) -> str:
    path = Path(__file__).parent.parent / template_path
    with open(path, "r", encoding="utf-8") as f:
        template_text = f.read()
    template = Template(template_text)
    return template.render(**context)

def get_initial_history(session_id: str, ai_persona: dict, user_persona: dict):
    system_prompt_path = ai_persona.get("system_prompt", "fantasy_context_prompt.txt")
    rendered = render_prompt(system_prompt_path, {
        "user": user_persona,
        "ai": ai_persona
    })

    return [
        {"role": "system", "content": rendered}
    ]

def update_history(history: list, user_input: str) -> list:
    history.append({"role": "user", "content": user_input})
    return history

def save_history(session_id: str, history: list):
    with open(HISTORY_DIR / f"{session_id}.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_history(session_id: str) -> list:
    path = HISTORY_DIR / f"{session_id}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []
