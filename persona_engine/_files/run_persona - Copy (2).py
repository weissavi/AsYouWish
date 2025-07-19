
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


with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
    
debug_mode = config.get("debug_mode", False)

api_key = config.get("api_key", "")

default_persona = config.get("default_persona", "maureen_persona.json")
#with open("elevenlabs_key.txt", "r") as f:
#    elevenlabs_key = f.read().strip()

base_url = config["base_url"]
default_model = config["default_model"]
history_limit = config.get("history_limit", 10)
mic_index = config.get("mic_index", 0)

parser = argparse.ArgumentParser()
parser.add_argument("--persona", help="Path to persona file", default=default_persona)
args = parser.parse_args()

persona_file = Path(args.persona)
if persona_file.exists():
    with open(persona_file, "r", encoding="utf-8") as f:
        persona = json.load(f)
else:
    print(f"Persona file '{args.persona}' not found.")
    exit()

if "system_prompt" not in persona:
    print("[??] Error: persona file is missing 'system_prompt'. Cannot continue.")
    exit()

Path("Voice_Responses").mkdir(exist_ok=True)

with open("behavior_dict.json", "r", encoding="utf-8") as f:
    behavior_dict = json.load(f)


valid_moods = set(behavior_dict.keys())

def validate_mood(mood):
    if mood not in valid_moods:
        print(f"[??] Unknown mood: '{mood}'. Defaulting to 'blue'.")
        return "blue"
    return mood


# Load user persona (Avi) once globally
with open("avi_persona.json", "r", encoding="utf-8") as f:
    avi_data = json.load(f)

# Combine Avi's persona and the current system prompt of the loaded assistant
persona_prompt = {"role": "system", "content": persona.get("system_prompt", "")}
system_messages = [persona_prompt]

default_voice = persona.get("voice_id", "bIQlQ61Q7WgbyZAL7IWj")
history = system_messages.copy()
voice_queue = Queue()
context_mode = "chat"
last_dare = ""
last_mood = ""

pygame.mixer.init()

def run_free_will():
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


def speak(text, voice_id="en-US-JennyNeural"):
    try:
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join("Voice_Responses", f"response_{timestamp}.mp3")

        async def run_tts():
            communicate = edge_tts.Communicate(text, voice=voice_id)
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
        "messages": messages
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
            return "blue"
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"[API Error - Mood Only] {e}")
        return "blue"


def get_mood_signal():
    recent_msgs = history[-10:]
    conversation = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in recent_msgs])
    prompt = f"You are a mood analysis assistant. Based on the user's last few messages, assess the emotional and erotic intensity.\n\n{conversation}\n\nReturn one word only:"
    mood = ask_model_mood_only(prompt)
    if isinstance(mood, str):
        detected = mood.strip().lower()
        print(f"[??] Mood detected: {detected}")
        return detected
    return "blue"

def build_context_summary():
    context = f"The current mode is '{context_mode}'."
    if last_dare:
        context += f" The last active dare was: {last_dare}."
    context += f" The previous mood was: {last_mood}."
    return f"You are Maureen. {context} Respond according to the ongoing interaction. Continue naturally with awareness of past actions."

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
        "teasing": "blue",
        "enhanced": "blue"
    }
    mood = mood_aliases.get(mood, mood)
    mood = validate_mood(mood)
    print(f"[??] Using mood: {mood}")

    behavior_description = behavior_dict.get(mood, "Respond naturally.")
    context_summary = build_context_summary()
    messages_to_send = [
        {"role": "system", "content": persona["system_prompt"]},
        {"role": "system", "content": context_summary},
        {"role": "user", "content": f"Current mood is '{mood}'. Style: {behavior_description}"}
    ] + history[-history_limit:]

    response = complete_model_response(messages_to_send)
    history.append({"role": "assistant", "content": response})

    # replace astriccs and remove remiders
    if response.startswith("*Friendly reminder") or "symbol for my quotes" in response:
        response = ""

    response = response.replace("*", "")

    return response


def main():
    print(f"[Loaded persona: {persona.get('name', 'Unknown')}]")

    if debug_mode:
        print("==== SYSTEM PROMPT (Loaded from persona) ====")
        print(persona.get("system_prompt", "[No system prompt found]"))
        print("===============================================")

    print("[??] Type 'voice' to synthesize. Type 'exit' to quit.")

    # Start the free will loop
    global last_user_input_time
    last_user_input_time = datetime.now()
    run_free_will()

    while True:
        user_input = input("You: ")
        
        last_user_input_time = datetime.now()

        if user_input.lower() == "exit":
            break
        elif user_input.lower() == "voice":
            text = input("Text to speak: ")
            voice_queue.put(text)
            continue

        ai_reply = ask_model(user_input)
        print(f"AI: {ai_reply}")
        voice_queue.put(ai_reply)

if __name__ == "__main__":
    if config.get("allow_free_will", False) and persona.get("has_free_will", False):
        run_free_will()
    main()
