
from typing import List, Dict

_last_mood = None

def has_mood_changed(current_mood: str) -> bool:
    global _last_mood
    if current_mood != _last_mood:
        _last_mood = current_mood
        return True
    return False

def reset_conversation(system_prompt: str, user_input: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

def continue_conversation(previous_messages: List[Dict[str, str]], user_input: str) -> List[Dict[str, str]]:
    return previous_messages + [{"role": "user", "content": user_input}]
