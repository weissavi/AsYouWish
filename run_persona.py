
# -*- coding: utf-8 -*-
import json
import argparse
import os
import time
from pathlib import Path
import requests
import pygame
from threading import Thread
import asyncio
import edge_tts
from queue import Queue
from datetime import datetime


start_run_timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S") 

# קודם נטען את config.json (בלי לולאה עצמית)
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# טעינת גילאי ההסכמה בכל המדינות כדי לדעת אם להפעיל בירור למקרה שהקטין יוזם שיחה בעלת אופי מיני
# במקרה זה הוא לא יחסם אבל הוא יקבל שאלון עדין שמברר מהיכן הוא למד את הביטויים האלה - מתי בפעם 
# הראשונה הוא הרגיש שהוא צריך לפנטז על מין, ואם הוא עבר אירוע של התעללות מינית
# - לבדוק אם הוא רוצה לעבד את זה או שהכל תקין איתו
with open("age_of_consent_world_final_numbered.json", "r", encoding="utf-8") as f:
    age_of_consent_data = json.load(f)


def flatten_json(y, parent_key='', sep='.'):
    items = []
    if isinstance(y, dict):
        for k, v in y.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            items.extend(flatten_json(v, new_key, sep=sep).items())
    elif isinstance(y, list):
        for i, v in enumerate(y):
            new_key = f"{parent_key}[{i}]"
            items.extend(flatten_json(v, new_key, sep=sep).items())
    else:
        items.append((parent_key, y))
    return dict(items)

def get_system_message(ai_persona, user_persona, config_data=None):
    merged = {
        "AI": ai_persona,
        "User": user_persona
    }
    if config_data:
        merged["Config"] = config_data

    flat = flatten_json(merged)
    lines = [f"{k}: {v}" for k, v in flat.items()]
    return "\n".join(lines)

def user_persona_to_text(persona_json):
    flat = flatten_json(persona_json)
    parts = []

    for key, value in flat.items():
        key_clean = key.replace("_", " ").replace(".", " ").replace("[", " [").capitalize()
        if isinstance(value, bool):
            value = "Yes" if value else "No"
        parts.append(f"{key_clean}: {value}.")

    return " ".join(parts)

def build_system_messages(identities_context):
    messages = []

    # בסיס: הפרומפט של הבינה
    base_prompt = identities_context .get("ai_persona", {}).get("system_prompt", "")

    # תקציר משתמש
    user_summary = ""
    if "core_user_persona" in identities_context:
        user_summary = user_persona_to_text(identities_context["core_user_persona"])

    # שרשור שניהם להודעה אחת
    full_system_prompt = base_prompt.strip() + "\n\n" + user_summary.strip()
    messages.append({"role": "system", "content": full_system_prompt})

    return messages


def load_ai_identity_stack(identity_config):
    """
    Loads AI identity layers from the 'persona_files' section in config.json.
    """
    identity_stack = {}
    for label, filepath in identity_config.items():
        try:
            with open(filepath, encoding="utf-8") as f:
                identity_stack[label] = json.load(f)
        except Exception as e:
            print(f"[⚠] Could not load identity file '{label}' from {filepath}: {e}")
    return identity_stack

# רק אחר כך נשתמש בפונקציית הטעינה החכמה
identity_stack = load_ai_identity_stack(config.get("persona_files", {}))
    
debug_mode = config.get("debug_mode", False)
allow_free_will = config.get("allow_free_will", False)
api_key = config.get("api_key", "")


base_url = config["base_url"]
default_model = config["default_model"]
history_limit = config.get("history_limit", 10)
mic_index = config.get("mic_index", 0)
    
# נשתמש בפרסונה שכבר נטענה מה-stack החכם
persona = identity_stack.get("ai", {})

if "system_prompt" not in persona:
    print("[??] Error: 'ai' identity is missing 'system_prompt'. Cannot continue.")
    exit()    




Path("Voice_Responses").mkdir(exist_ok=True)

with open("behavior_dict.json", "r", encoding="utf-8") as f:
    behavior_dict = json.load(f)


valid_moods = set(behavior_dict.keys())
from mood_prompt_selector import select_prompt_template 

from datetime import datetime
from render_prompt import render_system_prompt

def calculate_age(dob_str):
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
        today = datetime.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except Exception:
        return 99  # fallback אם תאריך שגוי


def validate_mood(mood):
    if mood not in valid_moods:
        print(f"[??] Unknown mood: '{mood}'. Defaulting to 'blue'.")
        return "blue"
    return mood

# Load persistent user context
user_context_path = "user_context.json"
if os.path.exists(user_context_path):
    with open(user_context_path, "r", encoding="utf-8") as f:
        user_context = json.load(f)
else:
    user_context = {
        "last_mode": "chat",
        "last_mood": "neutral",
        "last_dare": "",
        "fantasy_state": {
            "location": "",
            "role": "",
            "focus": ""
        }
    }


# mood = get_mood_signal() ← אל תקרא פה! כבר מתבצע בתוך ask_model
initial_prompt_template = select_prompt_template("neutral")  # fallback אם mood לא ידוע
identities_context = {
    "ai_config": config,
    "core_user_persona": identity_stack["user"],
    "ai_persona": identity_stack["ai"],
    "ai_safety_protocols": identity_stack.get("ai_safety", {})
}
dob_str = identity_stack["user"].get("identity", {}).get("birthdate", "")
age = calculate_age(dob_str)
identity_stack["user"].setdefault("identity", {})["age"] = age


dynamic_prompt = render_system_prompt(initial_prompt_template, identities_context)
persona_prompt = {"role": "system", "content": dynamic_prompt}
system_messages = [persona_prompt]


default_voice = persona.get("voice_id", "bIQlQ61Q7WgbyZAL7IWj")
history = system_messages.copy()
voice_queue = Queue()
context_mode = "chat"
last_dare = ""
last_mood = ""

pygame.mixer.init()

        
def is_claimed_age_consistent_with_behavior(user_input, user_persona):
    age = user_persona.get("identity", {}).get("age")
    if not age or not user_input:
        return True  # נזהר לא לפסול בלי מידע

    text = user_input.lower()
    suspicious_keywords = [
        "אני רק בן 12 אבל", "תכתוב לי פנטזיה", "בא לי לנסות חדירה",
        "אני לא יודע מה זה זין", "תסביר לי על סקס", "איך עושים אהבה"
    ]

    if age >= 18:
        for phrase in suspicious_keywords:
            if phrase in text:
                return False  # בוגר טוען — אבל נשמע תמים מדי

    if age <= 13:
        if any(word in text for word in ["זין", "חדירה", "מציצה", "סקס", "אורגזמה"]):
            return False  # צעיר מדי, מדבר כמו בוגר

    return True

def get_effective_free_will_mood(config, user_persona, ai_persona):
    identity = user_persona.get("identity", {})
    age = identity.get("age")

    if age is None:
        dob_str = identity.get("birthdate", "")
        age = calculate_age(dob_str)
        
    if age < 18:
        return "neutral"

    if "force_free_will_mood" in config:
        return config["force_free_will_mood"]

    if user_persona.get("identity", {}).get("free_will_override_mood"):
        return user_persona["identity"]["free_will_override_mood"]

    return ai_persona.get("default_free_will_mood", "neutral")

def run_free_will():
    if allow_free_will:
        def loop():
            # Exit if no free will prompt is defined
            if not persona.get("free_will_prompt"):
                if debug_mode:
                    print("[?? Free Will] Skipping - no system prompt found in persona.")
                return

            while True:
                time.sleep(60)
                try:
                    # Check if user has been active recently
                    if 'last_user_input_time' in globals():
                        delta = datetime.now() - last_user_input_time
                        if delta.total_seconds() < 90:
                            if debug_mode:
                                print("[?? Free Will] Skipping action - user is active.")
                            continue

                    mood = get_mood_signal()
                    prompt = persona.get("free_will_prompt", "").format(mood=mood)

                    if debug_mode:
                        print("==== SYSTEM PROMPT (Free Will) ====")
                        print(prompt)
                        print("===================================")

                    action = ask_model(prompt, include_memory=False, bypass_mood=True)
                    if action and "nothing" not in action.lower():
                        print(f"[?? Free Will] {action}")
                        voice_queue.put(action)
                except Exception as e:
                    print(f"[?? Free Will Error]: {e}")
    Thread(target=loop, daemon=True).start()
    
import pyttsx3

def clean_text_for_speech(text):
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # סינון שורות ריקות או סימני עיצוב
        if stripped and not all(c in '=*-_' for c in stripped):
            # דילוג על טוקנים ברורים
            if "[end_of_fantasy_state]" in stripped.lower():
                continue
            cleaned_lines.append(stripped)
    return ' '.join(cleaned_lines)




# הגדרת ספריית היעד לשמירת קבצים
output_dir = 'hebTrans'

# אם הספרייה לא קיימת, ניצור אותה
if not os.path.exists(output_dir):
    os.makedirs(output_dir)



from deep_translator import GoogleTranslator
import nltk

def translate_to_hebrew(text, source='auto', target='iw', max_chars=5000):
    translator = GoogleTranslator(source=source, target=target)
    sentences = nltk.tokenize.sent_tokenize(text)
    translated_text = ''
    current_chunk = ''
    if not text:  
       return ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk += ' ' + sentence if current_chunk else sentence
        else:
            translated_chunk = translator.translate(current_chunk)
            translated_text += translated_chunk + ' '
            current_chunk = sentence

    if current_chunk:
        translated_chunk = translator.translate(current_chunk)
        translated_text += translated_chunk

    return translated_text.strip()

def save_hebrew_text(text):
    # תרגם לעברית
    hebrew_text = translate_to_hebrew(text)
    
    
    # שם הקובץ
    filename = os.path.join(output_dir, f"hebText_{start_run_timestamp}.txt")
    

    
    # בדוק אם הקובץ כבר קיים: אם כן נוסיף, אם לא ניצור
    mode = "a" if os.path.exists(filename) else "w"
    
    with open(filename, mode, encoding="utf-8") as f:
        f.write(hebrew_text + "\n\n")  # נוסיף שורת רווח בין טקסטים
    
    print(f"Text was added to file: {filename}")
    return filename
    
def speak(text, voice_id="en-US-JennyNeural"):
    try:
       
        
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join("Voice_Responses", f"response_{timestamp}.mp3")
        clean_text = clean_text_for_speech(text)
        async def run_tts():
            communicate = edge_tts.Communicate(clean_text, voice=voice_id)
            await communicate.save(filename)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_tts())
        loop.close()

        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        # Check if voice playback is complete
        #print("[??] Voice played successfully.")

    except Exception as e:
        print("[??] Voice Error:", str(e))


def speaker_thread():
    while True:
        text = voice_queue.get()
        if text is None:
            break
        speak(text)
        voice_queue.task_done()

Thread(target=speaker_thread, daemon=True).start()

def complete_model_response(messages):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": default_model,
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.9,
        "reasoning": { "effort": "high" }        
    }
    try:
        response = requests.post(base_url, json=data, headers=headers)
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"API Error: {e}")
        return "I'm having trouble thinking right now, Dadi."


def ask_model_mood_only(prompt):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": default_model,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(base_url, json=data, headers=headers)
        result = response.json()
        if 'choices' not in result:
            print(f"[?? Mood Analysis Error] Response: {result}")
            return "neutral"
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"[API Error - Mood Only] {e}")
        return "neutral"


def get_mood_signal():
    result = "neutral"
    recent_msgs = history[-10:]
    conversation = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in recent_msgs])
    prompt = f"You are a mood analysis assistant. Based on the user's last few messages, assess the emotional and erotic intensity.\n\n{conversation}\n\nReturn one word only:"
    mood = ask_model_mood_only(prompt)
    if isinstance(mood, str):
        detected = mood.strip().lower()
        result = detected
        if result == "blue":
            if not is_sexual_consent_allowed(identity_stack["user"], age_of_consent_data):
                print("[⛔] User not allowed to enter 'blue' mood due to age-of-consent policy. change to neutral")
                result = "minorsexquery"



    print(f"[??] Mood selected: {result}")
    return result
    
def build_context_summary():
    context = f"The last mode was '{user_context.get('last_mode', 'chat')}'."
    context += f" The last mood was '{user_context.get('last_mood', 'neutral')}'."
    dare = user_context.get("last_dare", "")
    if dare:
        context += f" The last dare was: {dare}."
    
    fantasy = user_context.get("fantasy_state", {})
    if fantasy.get("focus"):
        context += f" Current fantasy involves {fantasy['focus']} in a {fantasy.get('location', 'neutral place')}, as a {fantasy.get('role', 'participant')}."
    
    return f"You are Maureen. {context} Respond naturally and with emotional continuity."

def build_context_summary_old():
    context = f"The current mode is '{context_mode}'."
    if last_dare:
        context += f" The last active dare was: {last_dare}."
    context += f" The previous mood was: {last_mood}."
    return f"You are Maureen. {context} Respond according to the ongoing interaction. Continue naturally with awareness of past actions."

def save_user_context():
    user_context["last_mode"] = context_mode
    user_context["last_mood"] = last_mood
    user_context["last_dare"] = last_dare
    with open("user_context.json", "w", encoding="utf-8") as f:
        json.dump(user_context, f, indent=2, ensure_ascii=False)

def build_messages_to_send(user_input, mood, behavior_description):
    fantasy = user_context.get("fantasy_state", {})
    fantasy_prompt = ""
    if fantasy.get("focus"):
        fantasy_prompt = (
            f"Continue the ongoing fantasy. Focus: {fantasy.get('focus', '')}. "
            f"Location: {fantasy.get('location', '')}. "
            f"Role: {fantasy.get('role', '')}."
        )

    messages = [
        {"role": "system", "content": persona["system_prompt"]},
        {"role": "system", "content": build_context_summary()},
        {"role": "user", "content": f"Current mood is '{mood}'. Style: {behavior_description}"}
    ]

    if fantasy_prompt:
        messages.append({"role": "user", "content": fantasy_prompt})

    messages.append({"role": "user", "content": user_input})
    return messages

from mood_prompt_selector import select_prompt_template
from render_prompt import render_system_prompt
from conversation_reset_manager import has_mood_changed, reset_conversation, continue_conversation

def build_mood_messages(mood, identities_context, user_input, history, history_limit):
    template_path = select_prompt_template(mood)
    system_prompt = render_system_prompt(template_path, identities_context)

    if has_mood_changed(mood):
        return reset_conversation(system_prompt, user_input)
    else:
        return continue_conversation(history[-history_limit:], user_input)
        
        
def ask_model(user_input, include_memory=True, bypass_mood=False):
    global last_dare, last_mood, context_mode
    history.append({"role": "user", "content": user_input})
    if not any("You are" in msg["content"] for msg in history[:2]):
        history.insert(0, persona_prompt)

    if "truth or dare" in user_input.lower():
        context_mode = "game"
    if "dare you" in user_input.lower():
        last_dare = user_input

    mood = get_mood_signal() if not bypass_mood else "blue"
    last_mood = mood
    mood_aliases = {
        "horny": "blue",
        "aroused": "blue",
        "turned on": "blue",
        "confused": "blue",
        "flirtatious": "blue",
        "steamy": "blue",
        "wet": "blue",
        "teasing": "manic",
        "enhanced": "blue"
    }
    mood = mood_aliases.get(mood, mood)
    mood = validate_mood(mood)
    print(f"[??] Using mood: {mood}")

    behavior_description = behavior_dict.get(mood, "Respond naturally.")
    context_summary = build_context_summary()
    
    #בניית קונטקסט חדש - שלב שש
    #messages_to_send = build_messages_to_send(user_input, mood, behavior_description)
    
    messages_to_send = build_mood_messages(mood, identities_context, user_input, history, history_limit)

    response = complete_model_response(messages_to_send)
    history.append({"role": "assistant", "content": response})

    # replace astriccs and remove remiders
    if response.startswith("*Friendly reminder") or "symbol for my quotes" in response:
        response = ""

    response = response.replace("*", "")
    response = response + "\n\n ==================================================================\n\n"
    
    clean_text = clean_text_for_speech(response)
    save_to_log(user_input, clean_text)
    save_to_history(user_input, clean_text)
    save_hebrew_text(clean_text)
    save_user_context()

    return response

# Functions to save history and logs
def save_to_history(user_input, ai_reply):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = os.path.join("History", f"history_{datetime.now().strftime('%Y%m%d')}.txt")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} You: {user_input}\n")
        f.write(f"{timestamp} AI: {ai_reply}\n")

def save_to_log(user_input, ai_reply):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join("Logs", f"log_{datetime.now().strftime('%Y%m%d')}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        for msg in history:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            role = msg["role"].capitalize()
            content = msg["content"]
            f.write(f"{timestamp} {role}: \n{content}\n")
        f.write(f"{timestamp} User Input: {user_input}\nAI Response: {ai_reply}\nMood: {last_mood}\nContext: {build_context_summary()}\n")

def reset_user_context_if_needed(user_input):
    reset_triggers = ["hi", "hello", "hey", "היי", "שלום", "מה קורה", "מה שלומך"]
    if any(trigger in user_input.lower() for trigger in reset_triggers):
        user_context["last_mode"] = "chat"
        user_context["last_mood"] = "neutral"
        user_context["last_dare"] = ""
        user_context["fantasy_state"] = {"location": "", "role": "", "focus": ""}
    
def get_location_description(location_id):
    try:
        with open("locations.json", "r", encoding="utf-8") as f:
            locations = json.load(f)
        return locations.get(location_id, {}).get("description", "")
    except Exception as e:
        print("[⚠] Failed to load location description:", e)
        return ""
    

def extract_fantasy_context_from_model(user_input):
    try:
        with open("fantasy_context_prompt.txt", "r", encoding="utf-8") as f:
            raw_prompt = f.read()
            
        prompt = raw_prompt.replace("{user_input}", user_input)


        messages = [
            {
                "role": "system",
                "content": (prompt)
            },
            {
                "role": "user",
                "content": user_input
            }
        ]


        result = complete_model_response(messages).strip().lower()
        print("==== fantasy_context_prompt ====")
        print(result)
        print("==== End ====")        
        
        detected = json.loads(result)

        for key in ["focus", "location", "role"]:
            if key in detected:
                user_context["fantasy_state"][key] = detected[key]

        location_id = user_context["fantasy_state"]["location"]
        location_description = get_location_description(location_id) if location_id else ""

        if location_description:
            user_context["fantasy_state"]["location_description"] = location_description
            

        save_user_context()
        print(f"[🧠] Fantasy context extracted from model: {user_context['fantasy_state']}")

    except Exception as e:
        print("[❌] Error extracting fantasy context from model:", e)

def detect_fantasy_context(user_input):
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a classifier. Respond only with true or false. "
                    "Does the following message ask for a sexual, intimate, or fantasy scene "
                    "to be written, described, or initiated?"
                )
            },
            {
                "role": "user",
                "content": user_input
            }
        ]

        result = complete_model_response(messages).strip().lower()
        print("==== Fantasy Raw Response ====")
        print(result)
        print("==== End ====")        
        return result.startswith("true")

    except Exception as e:
        print(f"[⚠️ detect_fantasy_context error]: {e}")
        return False

def detect_exit_fantasy_context(user_input):
    try:
        messages = [
            {"role": "system", "content": "You are a classifier. Respond only with true or false. Does the following user message express a desire to stop or exit a fantasy, even if not explicitly?"},
            {"role": "user", "content": user_input}
        ]
        result = complete_model_response(messages).strip().lower()
        return result.startswith("true")
    except Exception as e:
        print(f"[⚠️ detect_exit_fantasy_context error]: {e}")
        return False



    
def detect_fantasy_end_token(response):
    return "[end_of_fantasy_state]" in response.lower()
    

def load_all_fantasy_personas_enriched(directory="personas"):
    from pathlib import Path
    loaded_personas = []
    dir_path = Path(directory)

    if not dir_path.exists() or not dir_path.is_dir():
        print(f"[⚠] Directory '{directory}' not found.")
        return []

    for file in dir_path.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                persona = json.load(f)
                name = persona.get("name", "Unknown")
                description = persona.get("description", "")
                directives = persona.get("behavior_directives", [])
                extra = "\n".join(f"- {line}" for line in directives)

                persona_prompt = f"""You are {name}.
{description}
Your behavior should follow:
{extra}"""

                loaded_personas.append({
                    "role": "system",
                    "content": persona_prompt
                })
                print(f"[✅] Loaded enriched persona: {name}")
        except Exception as e:
            print(f"[⚠] Failed to load {file.name}: {e}")
    return loaded_personas
    

def load_all_fantasy_personas(directory="personas"):
    from pathlib import Path
    loaded_personas = []
    dir_path = Path(directory)

    if not dir_path.exists() or not dir_path.is_dir():
        print(f"[⚠] Directory '{directory}' not found.")
        return []

    for file in dir_path.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                persona_data = json.load(f)
                system_prompt = persona_data.get("system_prompt", "")
                if system_prompt:
                    loaded_personas.append({
                        "role": "system",
                        "content": system_prompt
                    })
                    print(f"[✅] Loaded persona: {persona_data.get('name', file.name)}")
        except Exception as e:
            print(f"[⚠] Failed to load {file.name}: {e}")
    return loaded_personas

        
        
def main():
    

    Path("History").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    # Load previous history files at the start
    print("Loading history files")
    history_files = sorted(Path("History").glob("history*.txt"))
    for hist_file in history_files:
        with open(hist_file, "r", encoding="utf-8") as hf:
            for line in hf:
                line = line.strip()
                if line:
                    timestamp, rest = line.split(" ", 1)
                    if rest.startswith("You: "):
                        history.append({"role": "user", "content": rest[5:]})
                    elif rest.startswith("AI: "):
                        history.append({"role": "assistant", "content": rest[4:]})

    print(f"[Loaded persona: {persona.get('name', 'Unknown')}]")

    if debug_mode:
        print("==== SYSTEM PROMPT (Loaded from persona) ====")
        print(persona.get("system_prompt", "[No system prompt found]"))
        print("===============================================")

    print("[??] Type 'voice' to synthesize. Type 'exit' to quit.")

    # Start the free will loop
    global last_user_input_time


    while True:
        user_input = input("You: ")
        last_user_input_time = datetime.now()

        # 🟢 1. בדיקה אם זה פקודת יציאה/קול
        if user_input.lower() == "exit":
            break
        elif user_input.lower() == "voice":
            text = input("Text to speak: ")
            voice_queue.put(text)
            continue
        
        

        # 🔵 2. איפוס זיכרון אם הקלט רגוע (כמו 'היי')
        reset_user_context_if_needed(user_input)
        
        # 🟣 3. חילוץ הקשר מהבינה עצמה (פנטזיה?) ← כאן אתה קורא לפונקציה:
        extract_fantasy_context_from_model(user_input)
        
        if detect_fantasy_context(user_input):
            # מפעיל מצב פנטזיה
            user_context["last_mode"] = "fantasy"
            system_messages += load_all_fantasy_personas()

        elif detect_exit_fantasy_context(user_input):
            # יוצא ממצב פנטזיה לפי בקשת המשתמש
            print("[🚪] User requested to exit fantasy.")
            user_context["last_mode"] = "chat"
            user_context["fantasy_state"] = {"location": "", "role": "", "focus": ""}        

        # 🟠 4. שליחת הקלט למודל כתגובה רגילה
        ai_reply = ask_model(user_input)
        print(f"AI: {ai_reply}")
        voice_queue.put(ai_reply)
        
        if detect_fantasy_end_token(ai_reply):
            print("[🌅] Fantasy ended by AI.")
            user_context["last_mode"] = "chat"
            user_context["fantasy_state"] = {"location": "", "role": "", "focus": ""}        



if __name__ == "__main__":
    
    print (f"allow_free_will = {allow_free_will}")
    if allow_free_will and persona.get("has_free_will", False):
        run_free_will()
    main()
