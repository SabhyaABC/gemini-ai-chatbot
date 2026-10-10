import os, time, secrets, hmac
from threading import Lock
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from werkzeug.security import check_password_hash
from google import genai

load_dotenv()
MODEL_NAME = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
MAX_RETRIES = 5
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE','false').lower() == 'true')
USERNAME = os.getenv('CHAT_USERNAME', 'admin')
PASSWORD = os.getenv('CHAT_PASSWORD', '')
PASSWORD_HASH = os.getenv('CHAT_PASSWORD_HASH', '')
client = None
client_lock, chats_lock = Lock(), Lock()
chats = {}

def authenticated(): return session.get('authenticated') is True

def valid_login(username, password):
    if not PASSWORD and not PASSWORD_HASH: return False
    user_ok = hmac.compare_digest(username, USERNAME)
    pass_ok = check_password_hash(PASSWORD_HASH, password) if PASSWORD_HASH else hmac.compare_digest(password, PASSWORD)
    return user_ok and pass_ok

def get_client():
    global client
    with client_lock:
        if client is None:
            key = os.getenv('GEMINI_API_KEY')
            if not key: raise RuntimeError('GEMINI_API_KEY is missing. Add it to your .env file.')
            client = genai.Client(api_key=key)
    return client

def send_with_retry(chat, message):
    for attempt in range(MAX_RETRIES):
        try: return chat.send_message(message)
        except Exception as exc:
            busy = '503' in str(exc) or 'UNAVAILABLE' in str(exc)
            if busy and attempt < MAX_RETRIES - 1: time.sleep(2 ** attempt)
            elif busy: raise RuntimeError('The AI model is busy. Please try again shortly.') from exc
            else: raise RuntimeError(f'Could not connect to the AI model: {exc}') from exc

@app.get('/')
def home():
    if not authenticated(): return redirect(url_for('login_page'))
    return render_template('index.html', model=MODEL_NAME)

@app.get('/login')
def login_page():
    if authenticated(): return redirect(url_for('home'))
    return render_template('login.html')

@app.post('/api/login')
def api_login():
    data = request.get_json(silent=True) or {}
    username, password = str(data.get('username') or ''), str(data.get('password') or '')
    if not valid_login(username, password): return jsonify(error='Incorrect username or password.'), 401
    session.clear(); session['authenticated'] = True; session['chat_id'] = secrets.token_urlsafe(18)
    return jsonify(ok=True)

@app.post('/api/logout')
def api_logout():
    chat_id = session.get('chat_id')
    if chat_id:
        with chats_lock: chats.pop(chat_id, None)
    session.clear()
    return jsonify(ok=True)

@app.post('/api/reset')
def reset_chat():
    if not authenticated(): return jsonify(error='Please log in.'), 401
    old = session.get('chat_id')
    if old:
        with chats_lock: chats.pop(old, None)
    session['chat_id'] = secrets.token_urlsafe(18)
    return jsonify(ok=True)

@app.post('/api/chat')
def chat():
    if not authenticated(): return jsonify(error='Please log in.'), 401
    message = str((request.get_json(silent=True) or {}).get('message') or '').strip()
    if not message: return jsonify(error='Please type a message first.'), 400
    if len(message) > 12000: return jsonify(error='Message too long (maximum 12,000 characters).'), 400
    chat_id = session.get('chat_id') or secrets.token_urlsafe(18)
    session['chat_id'] = chat_id
    try:
        with chats_lock:
            if chat_id not in chats: chats[chat_id] = get_client().chats.create(model=MODEL_NAME)
            active_chat = chats[chat_id]
        response = send_with_retry(active_chat, message)
        answer = getattr(response, 'text', None) if response else None
        if not answer: return jsonify(error='The model returned an empty response. Please try again.'), 502
        return jsonify(reply=answer)
    except Exception as exc: return jsonify(error=str(exc)), 502

if __name__ == '__main__': app.run(host='127.0.0.1', port=5000, debug=False)
