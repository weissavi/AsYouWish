# === mood_prompt_selector.py ===
from pathlib import Path

def select_prompt_template(mood: str, base_dir: str = "SystemPromptTemplates") -> Path:
    """
    Selects the appropriate system prompt template based on the user's mood.
    Raises FileNotFoundError if the template does not exist.
    """
    path = Path(base_dir) / f"{mood}_prompt.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found for mood '{mood}' at path: {path}")
    return path