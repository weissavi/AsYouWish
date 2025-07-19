
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_persona(file_path: str) -> dict:
    path = Path(__file__).parent.parent / file_path
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
