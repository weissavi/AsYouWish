from flask import Flask, render_template, request, session, jsonify, url_for, redirect
import uuid
import os, json, hashlib, secrets
from pathlib import Path
from persona_engine.core import generate_fantasy
from persona_engine.context import load_history, save_history

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = secrets.token_hex(16)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_DIR = os.path.join(BASE_DIR, "user_data")
SCHEMA_PATH = os.path.join(BASE_DIR, "character_creation_schema.json")

def get_current_user():
    username = session.get("username", "avi")
    
    if app.debug:
        session["username"] = "avi"
        return "avi"
    
    return username    

def get_user_or_redirect():
    username = get_current_user()
    if not username:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return None  # תמשיך, ה-API יתמודד
        else:
            return redirect(url_for("index"))
    return username

def build_fantasy_prompt(character_name, template_path="fantasy_prompt_template.txt"):
    username = get_current_user()
    user_path = os.path.join(USER_DATA_DIR, username)
    character_file = os.path.join(user_path, f"{character_name}.json")

    # טען את קובץ הדמות המאוחד
    with open(character_file, encoding="utf-8") as f:
        full_data = json.load(f)

    user_data = full_data.get("user_profile", {})
    ai_data = full_data.get("ai_profile", {})

    # טען את תבנית הפרומפט
    with open(template_path, encoding="utf-8") as f:
        template = f.read()

    # טען סכימה למציאת תרגום של content_types
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)

    # מיפוי מפתחות לתוויות
    content_type_field = next((f for f in schema if f["field"] == "content_types"), None)
    label_lookup = {}
    if content_type_field and "options" in content_type_field:
        label_lookup = {
            opt.get("key"): opt.get("ai_prompt") or opt.get("label") or opt.get("key")
            for opt in content_type_field["options"]
        }

    # מיזוג כל הנתונים הנדרשים
    merged = {**user_data, **ai_data}

    # עיבוד content_types
    if isinstance(merged.get("content_types"), list):
        labels = [label_lookup.get(k, k) for k in merged["content_types"]]
        merged["content_types"] = ", ".join(labels)

    # ברירת מחדל לשדות חסרים
    for key in ["other_gender", "voice_preference", "vibe"]:
        merged.setdefault(key, "")

    # צור את הפרומפט הסופי
    return template.format(**merged)


def build_fantasy_prompt_old(character_name, template_path="fantasy_prompt_template.txt"):
    username = get_current_user()
    user_path = os.path.join(USER_DATA_DIR, username)

    user_file = os.path.join(user_path, f"{character_name}_user_profile.json")
    ai_file = os.path.join(user_path, f"{character_name}_ai_persona.json")

    with open(user_file, encoding="utf-8") as f:
        user_data = json.load(f)
    with open(ai_file, encoding="utf-8") as f:
        ai_data = json.load(f)
    with open(template_path, encoding="utf-8") as f:
        template = f.read()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)

    # תרגום content_types
    content_type_field = next((f for f in schema if f["field"] == "content_types"), None)
    label_lookup = {}
    if content_type_field and "options" in content_type_field:
        label_lookup = {
            opt.get("key"): opt.get("ai_prompt") or opt.get("label") or opt.get("key")
            for opt in content_type_field["options"]
        }

    # מיזוג נתונים
    merged = {**user_data, **ai_data}

    if isinstance(merged.get("content_types"), list):
        labels = [label_lookup.get(k, k) for k in merged["content_types"]]
        merged["content_types"] = ", ".join(labels)

    for key in ["other_gender", "voice_preference", "vibe"]:
        merged.setdefault(key, "")

    return template.format(**merged)
    
def hash_password(password, salt=None):
    if not salt:
        salt = secrets.token_hex(8)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return hashed, salt

def verify_password(password, stored_hash, salt):
    return hashlib.sha256((salt + password).encode()).hexdigest() == stored_hash


@app.route("/", methods=["GET"])
def index():
    retUser = None
    retSchema =[]
    
    if "username" in session:
        retUser = get_current_user()

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        retSchema = json.load(f)
        
    return render_template("index.html", username=retUser,schema=retSchema)        
    
@app.route("/prompt/<character_name>", methods=["GET"])
def debug_prompt(character_name):
    username = get_current_user()
    if not username:
        return "❌ User not logged in", 403

    try:
        prompt = build_fantasy_prompt(character_name)
        return f"<pre>{prompt}</pre>"
    except Exception as e:
        return f"❌ Error: {str(e)}", 500

@app.route("/send", methods=["POST"])
def send():
    username = get_current_user()
    if not username:
        return "❌ User not logged in", 403
    
    user_input = request.json.get("message", "")
    session_id = session.get("session_id")
    if not session_id:
        return jsonify({"error": "Session not found"}), 400

    reply = generate_fantasy(user_input, session_id)
    history = load_history(session_id)
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})
    save_history(session_id, history)

    return jsonify({"reply": reply})
    
 
@app.route("/create_character", methods=["GET"])
def create_character_form():
    username = get_current_user()
    if not username:
        return redirect("/register")

    with open(SCHEMA_PATH, encoding='utf-8') as f:
        schema = json.load(f)
    return render_template("character_creation.html", schema=schema)    

@app.route("/schema")
def schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "application/json"}

@app.route("/list_characters", methods=["GET"])
def list_characters():
    username = get_current_user()
    if not username:
        return jsonify({"error": "User not logged in"}), 403

    user_dir = os.path.join(USER_DATA_DIR, username)
    if not os.path.exists(user_dir):
        return jsonify({"characters": []})

    characters = []
    for fname in os.listdir(user_dir):
        if fname.endswith(".json") and not fname.startswith(("auth", "meta", "settings")):
            char_name = os.path.splitext(fname)[0]
            characters.append(char_name)

    return jsonify({"characters": sorted(characters)})

@app.route("/characters", methods=["GET"])
def character_list_page():
    username = get_current_user()
    if not username:
        return redirect("/register")
    
    return render_template("character_list.html")

@app.route("/save_character", methods=["POST"])
def save_character():
    username = get_current_user()
    if not username:
       return jsonify({"error": "user not logged in"}), 403

    data = request.get_json()

    with open(SCHEMA_PATH, encoding='utf-8') as f:
        schema = json.load(f)

    user_data = {}
    ai_data = {}

    for field in schema:
        key = field["field"]
        target = field.get("target", "user_profile")
        if key in data:
            (ai_data if target == "ai_profile" else user_data)[key] = data[key]

    user_dir = os.path.join(USER_DATA_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    character_name = user_data["name"]

    combined = {
        "user_profile": user_data,
        "ai_profile": ai_data
    }
    character_file = os.path.join(user_dir , f"{character_name}.json")
    with open(character_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    #system_prompt = build_fantasy_prompt(character_name)
    #print(system_prompt)

    return jsonify({"success": True})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            data = request.get_json()
            username = data["username"].strip().lower()
            password = data["password"]
        except Exception:
            return jsonify({"error": "Invalid input"}), 400

        user_path = os.path.join(USER_DATA_DIR, username)
        auth_file = os.path.join(user_path, "auth.json")

        if not os.path.exists(auth_file):
            return jsonify({"error": "User does not exist"}), 400

        with open(auth_file, "r") as f:
            auth_data = json.load(f)

        if not verify_password(password, auth_data["password_hash"], auth_data["salt"]):
            return jsonify({"error": "Incorrect password"}), 403

        session["username"] = username
        return jsonify({"redirect": "/"})

    return render_template("login.html")
    
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            data = request.get_json()
            username = data["username"].strip().lower()
            password = data["password"]
        except Exception:
            return jsonify({"error": "Invalid input"}), 400

        user_path = os.path.join(USER_DATA_DIR, username)
        auth_file = os.path.join(user_path, "auth.json")

        if os.path.exists(auth_file):
            return jsonify({"error": "Username already exists. Please choose another."}), 400

        os.makedirs(user_path, exist_ok=True)
        hashed_pw, salt = hash_password(password)

        with open(auth_file, "w") as f:
            json.dump({"password_hash": hashed_pw, "salt": salt}, f)

        session["username"] = username
        return jsonify({"redirect": "/create_character"})

    return render_template("register.html")

    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        user_path = os.path.join(USER_DATA_DIR, username)
        auth_file = os.path.join(user_path, "auth.json")

        if os.path.exists(auth_file):
            return "Username already exists. Please choose another.", 400

        os.makedirs(user_path, exist_ok=True)
        hashed_pw, salt = hash_password(password)

        with open(auth_file, "w") as f:
            json.dump({"password_hash": hashed_pw, "salt": salt}, f)

        session["username"] = username
        return redirect("/create_character")

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
    
if __name__ == "__main__":
    app.run(debug=True)
    

