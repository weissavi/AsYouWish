# guided_mode_selector.py

from pathlib import Path
import requests
import json
from jinja2 import Template


def render_prompt_template(template_path: str, context: dict) -> str:
    """
    Renders a Jinja2 template file with provided context.
    """
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_text = f.read()
        template = Template(template_text)
        return template.render(**context)
    except Exception as e:
        print("[Prompt Render Error]", e)
        return ""


def ask_model_for_mode_classification(user_input, api_key, config, model="mistralai/mistral-7b-instruct"):
    """
    Sends the user input to an LLM to classify it as:
    - 'gabor' or 'esther' if it matches
    - otherwise returns 'custom' and includes the user idea
    Loads prompt path from config and uses Jinja2 for substitution.
    """
    prompt_file_path = config.get("mode_classification_prompt", "prompts/mode_classifier_prompt.txt")
    context = {"user_input": user_input}  # Could be extended later with persona info

    prompt = render_prompt_template(prompt_file_path, context)
    if not prompt:
        return {"mode": "minorsexquery"}

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }
    )

    try:
        result = response.json()
        content = result['choices'][0]['message']['content']
        return json.loads(content)
    except Exception as e:
        print("[Classification Error]", e)
        return {"mode": "minorsexquery"}


def get_guided_prompt_path():
    prompt_file = Path("prompts/guided_mode_intro.txt")
    if prompt_file.exists():
        return prompt_file
    else:
        return None

