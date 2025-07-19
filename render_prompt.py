# === render_prompt.py ===
from jinja2 import Template
import json
def render_system_prompt(template_path, context_dict):
    """
    Renders a system prompt from a template and a context dictionary.
    """
    with open(template_path, "r", encoding="utf-8") as f:
        template_text = f.read()
    template = Template(template_text)
    return template.render(**context_dict)    
