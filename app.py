import os
import uuid
import sqlite3
import threading
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pydub import AudioSegment
from openai import OpenAI
import whisper

app = Flask(__name__, static_folder='.')
CORS(app)

# ==========================================
# CONFIGURATION
# ==========================================
API_KEY = "sk-K0UYE8QlMeFGcQ14afhOIXGy4MM2OjXGoaVH34aQqC7t2w0H"
STT_BASE_URL = "https://api.gapgpt.app/v1"
STT_MODEL = "gapgpt/whisper-1"

LLM_API_KEY = "sk-K0UYE8QlMeFGcQ14afhOIXGy4MM2OjXGoaVH34aQqC7t2w0H"
LLM_BASE_URL = "https://api.gapgpt.app/v1"
LLM_MODEL = "gpt-4o"

UPLOAD_FOLDER = "uploads"
MODELS_FOLDER = "models"
DB_PATH = "meetings.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MODELS_FOLDER, exist_ok=True)

progress_store: dict[str, dict] = {}
_whisper_cache = None

# ==========================================
# DATABASE
# ==========================================
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                title TEXT,
                subject TEXT,
                participants TEXT,
                date TEXT,
                audio_path TEXT,
                raw_text TEXT DEFAULT '',
                offline_text TEXT DEFAULT '',
                minutes TEXT,
                status TEXT DEFAULT 'created',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

init_db()

# ==========================================
# STT & LLM FUNCTIONS
# ==========================================
def process_audio_chunk_online(chunk_path):
    client = OpenAI(base_url=STT_BASE_URL, api_key=API_KEY)
    try:
        with open(chunk_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=STT_MODEL,
                file=audio_file,
                response_format="text"
            )
            return transcript.strip()
    except Exception as e:
        print(f"Online STT Chunk Error: {e}")
        return ""

def process_audio_chunk_offline(chunk_path):
    global _whisper_cache
    if _whisper_cache is None:
        _whisper_cache = whisper.load_model("large-v3", download_root=MODELS_FOLDER)
    try:
        result = _whisper_cache.transcribe(chunk_path, language="fa")
        return result["text"].strip()
    except Exception as e:
        print(f"Offline STT Chunk Error: {e}")
        return ""

def run_llm(prompt):
    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return resp.choices[0].message.content

# ==========================================
# ROUTES
# ==========================================
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/meetings', methods=['POST'])
def create_meeting():
    data = request.json
    mid = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO meetings (id, title, subject, participants, date) VALUES (?, ?, ?, ?, ?)",
            (mid, data.get('title'), data.get('subject'), data.get('participants'), data.get('date'))
        )
        conn.commit()
    return jsonify({"success": True, "meeting_id": mid})

@app.route('/api/meetings/<mid>/chunk', methods=['POST'])
def upload_chunk(mid):
    if 'audio' not in request.files:
        return jsonify({"success": False, "error": "No chunk provided"}), 400
    
    chunk = request.files['audio']
    do_online = request.form.get('run_online') == 'true'
    do_offline = request.form.get('run_offline') == 'true'
    
    # فایل کلی جلسه برای ذخیره دائم
    main_audio_path = os.path.join(UPLOAD_FOLDER, f"{mid}_main.webm")
    
    # فایل موقت برای پردازش همین تکه
    temp_chunk_path = os.path.join(UPLOAD_FOLDER, f"temp_{uuid.uuid4()}.webm")
    chunk.save(temp_chunk_path)
    
    # ذخیره در فایل اصلی روی هارد (Append) بدون نگه داشتن در رم
    with open(main_audio_path, "ab") as main_file:
        with open(temp_chunk_path, "rb") as temp_file:
            main_file.write(temp_file.read())
            
    online_text = ""
    offline_text = ""
    
    if do_online:
        online_text = process_audio_chunk_online(temp_chunk_path)
    if do_offline:
        offline_text = process_audio_chunk_offline(temp_chunk_path)
        
    os.remove(temp_chunk_path) # حذف فایل موقت
    
    # آپدیت دیتابیس
    with get_db() as conn:
        row = conn.execute("SELECT raw_text, offline_text FROM meetings WHERE id=?", (mid,)).fetchone()
        new_raw = (row['raw_text'] + " " + online_text).strip() if row['raw_text'] else online_text
        new_off = (row['offline_text'] + " " + offline_text).strip() if row['offline_text'] else offline_text
        
        conn.execute(
            "UPDATE meetings SET audio_path=?, raw_text=?, offline_text=?, status='stt_done' WHERE id=?",
            (main_audio_path, new_raw, new_off, mid)
        )
        conn.commit()
        
    return jsonify({
        "success": True,
        "online_chunk": online_text,
        "offline_chunk": offline_text
    })

@app.route('/api/meetings/<mid>/minutes', methods=['POST'])
def generate_minutes(mid):
    source = request.json.get('text_source', 'online')
    with get_db() as conn:
        row = conn.execute("SELECT * FROM meetings WHERE id=?", (mid,)).fetchone()
        
    if not row: return jsonify({"success": False, "error": "Meeting not found"}), 404
    
    text = ""
    if source == 'online': text = row['raw_text']
    elif source == 'offline': text = row['offline_text']
    else: text = f"[آنلاین]\n{row['raw_text']}\n\n[آفلاین]\n{row['offline_text']}"
    
    prompt = f"""شما یک دستیار حرفه‌ای برای تنظیم صورتجلسات هستید. بر اساس اطلاعات و متن پیاده‌سازی شده زیر، یک صورتجلسه رسمی و دقیق به زبان فارسی تهیه کنید.

عنوان جلسه: {row['title']}
موضوع: {row['subject']}
شرکت‌کنندگان: {row['participants']}
تاریخ: {row['date']}

متن مذاکرات:
{text}

لطفاً صورتجلسه را در بخش‌های زیر تنظیم کنید:
۱. اطلاعات کلی جلسه
۲. خلاصه مذاکرات
۳. تصمیمات اتخاذ‌شده
۴. اقدامات لازم و مسئولین مربوطه
۵. جمع‌بندی نهایی
"""
    try:
        minutes = run_llm(prompt)
        with get_db() as conn:
            conn.execute("UPDATE meetings SET minutes=?, status='done' WHERE id=?", (minutes, mid))
            conn.commit()
        return jsonify({"success": True, "minutes": minutes})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    msgs = request.json.get('messages', [])
    try:
        client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=msgs,
            temperature=0.7
        )
        return jsonify({"success": True, "reply": resp.choices[0].message.content})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/meetings', methods=['GET'])
def get_meetings():
    with get_db() as conn:
        rows = conn.execute("SELECT id, title, subject, participants, date, status, created_at FROM meetings ORDER BY created_at DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/meetings/<mid>', methods=['GET'])
def get_meeting(mid):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM meetings WHERE id=?", (mid,)).fetchone()
    if not row: return jsonify({"error": "Not found"}), 404
    return jsonify(dict(row))

@app.route('/api/meetings/<mid>', methods=['DELETE'])
def delete_meeting(mid):
    with get_db() as conn:
        row = conn.execute("SELECT audio_path FROM meetings WHERE id=?", (mid,)).fetchone()
        if row and row['audio_path'] and os.path.exists(row['audio_path']):
            try: os.remove(row['audio_path'])
            except: pass
        conn.execute("DELETE FROM meetings WHERE id=?", (mid,))
        conn.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
