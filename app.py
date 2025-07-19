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
        retUser=session["username"]

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        retSchema = json.load(f)
        
    return render_template("index.html", username=retUser,schema=retSchema)        
    
#def home():    
#    session_id = session.get("session_id")
#    if not session_id:
#        session_id = str(uuid.uuid4())
#        session["session_id"] = session_id

    #history = load_history(session_id)
    #return render_template("index.html", history=history)
    


@app.route("/send", methods=["POST"])
def send():
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

    
@app.route("/create_character", methods=["GET"])
def create_character_form():
    if "username" not in session:
        return redirect("/register")

    with open(SCHEMA_PATH, encoding='utf-8') as f:
        schema = json.load(f)
    return render_template("character_creation.html", schema=schema)    

@app.route("/schema")
def schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "application/json"}

@app.route("/save_character", methods=["POST"])
def save_character():
    if "username" not in session:
        return jsonify({"status": "error", "message": "User not logged in"}), 403

    username = session["username"]
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

    user_dir = os.path.join(USER_BASE_DIR, username)
    os.makedirs(user_dir, exist_ok=True)

    with open(os.path.join(user_dir, "user_profile.json"), "w", encoding="utf-8") as f:
        json.dump(user_data, f, indent=2, ensure_ascii=False)

    with open(os.path.join(user_dir, "ai_persona.json"), "w", encoding="utf-8") as f:
        json.dump(ai_data, f, indent=2, ensure_ascii=False)

    return jsonify({"success": True})



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
    
if __name__ == "__main__":
    app.run(debug=True)