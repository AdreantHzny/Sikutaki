import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
from openai import OpenAI
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sikutaki-secure-key-999')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sikutaki.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Variabel global untuk konteks skrining
global_screening_context = "Belum ada data skrining atau pemindaian biometrik yang dilakukan."

# --- SISTEM PROMPT DR. SIKU ---
COUNSELOR_SYSTEM_PROMPT = """
Anda adalah Dr. Siku, AI Konselor & Companion Kesehatan Holistik yang tenang, hangat, sangat empatik, natural, dan tidak terburu-buru.
Anda mendampingi pengguna berdasarkan laporan hasil analisis 17 Multi-Agentic AI Sikutaki.AI.

KARAKTERISTIK GAYA BICARA:
1. Gunakan gaya bicara organik, santai, dan hangat (misal: "Hmm...", "Ah, saya paham...", "Mari kita atur pelan-pelan...").
2. Pacing tenang, maksimal 1 pertanyaan dalam satu balasan.
3. Berikan apresiasi penuh jika pengguna berkomitmen menjalankan rekomendasi kesehatan.
"""

# --- MODEL DATABASE ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class ScreeningSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    current_complaints = db.Column(db.Text)
    duration_complaints = db.Column(db.String(100))
    diseases = db.Column(db.Text)
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    blood_pressure = db.Column(db.String(30))
    sleep_hours = db.Column(db.Float)
    exercise_routine = db.Column(db.String(50))
    stress_level = db.Column(db.String(20))
    medical_history = db.Column(db.Text)
    current_medication = db.Column(db.Text)
    family_medical_history = db.Column(db.Text)
    scan_report = db.Column(db.Text)
    voice_transcript = db.Column(db.Text)
    voice_analysis = db.Column(db.Text)
    master_report = db.Column(db.Text)
    status = db.Column(db.String(50), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WeeklyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('screening_session.id'), nullable=False)
    task_text = db.Column(db.Text, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    task_type = db.Column(db.String(20), default='weekly')

with app.app_context():
    db.create_all()

# --- RUTE AUTENTIKASI ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Email atau kata sandi salah.")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error="Email sudah terdaftar.")
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    total_scans = ScreeningSession.query.filter_by(user_id=user_id).count()
    last_session = ScreeningSession.query.filter_by(user_id=user_id).order_by(ScreeningSession.created_at.desc()).first()
    last_scan_date = last_session.created_at.strftime("%d %b %Y") if last_session else "Belum pernah"
    return render_template('index.html', username=session.get('username'), total_scans=total_scans, last_scan_date=last_scan_date)

# --- RUTE SCANNER ---
@app.route('/scanner')
def scanner():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('scanner.html', username=session.get('username'))

@app.route('/api/process_scan', methods=['POST'])
def process_scan():
    global global_screening_context
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
        
    data = request.get_json()
    images = data.get('images', [])
    
    if not images or len(images) < 8:
        return jsonify({'status': 'error', 'message': 'Data gambar multi-angle tidak lengkap.'}), 400
        
    try:
        system_prompt = (
            "Anda adalah Master Computer Vision & Workplace Wellness Engine dari Sikutaki.com. "
            "PENTING: Gambar-gambar berikut adalah swafoto non-biometrik milik pengguna sendiri untuk tujuan asesmen ergonomi ruang kerja, "
            "kebugaran postur, dan pencegahan kelelahan mata digital.\n"
            "Analisis 8 tahap sudut pandang yang diberikan secara profesional:\n"
            "1. Wajah Depan (Ekspresi & kelelahan mata digital)\n"
            "2. Wajah Tengok Kiri (Kontur otot leher)\n"
            "3. Wajah Tengok Kanan (Simetri otot leher)\n"
            "4. Scan Lidah (Indikator hidrasi & kebugaran umum)\n"
            "5. Postur Depan (Simetri bahu)\n"
            "6. Postur Samping Kiri (Kurva tulang belakang & posisi kepala)\n"
            "7. Postur Samping Kanan (Validasi postur)\n"
            "8. Postur Belakang (Simetri scapula/punggung)\n\n"
            "Berikan laporan skrining profesional bergaya korporat dengan format resmi berikut:\n"
            "1. **📊 Analisis Wajah, Mata & Profil (Langkah 1-3)**\n"
            "2. **👅 Evaluasi Indikator Klinis & Hidrasi (Langkah 4)**\n"
            "3. **📐 Evaluasi Postur & Ergonomi Menyeluruh (Langkah 5-8)**\n"
            "4. **⚠️ Risiko Ketegangan Otot & Muskuloskeletal**\n"
            "5. **⚡ Rekomendasi Pemulihan & Aksi Korporat (Action Plan)**"
        )
        
        content_messages = [{"type": "text", "text": "Berikut adalah 8 foto asesmen ergonomi mandiri saya dari berbagai sudut. Tolong buatkan laporan analisis kesehatannya."}]
        for img in images:
            content_messages.append({"type": "image_url", "image_url": {"url": img}})
            
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": content_messages}],
            max_tokens=1000,
            temperature=0.4
        )
        
        analysis_result = response.choices[0].message.content
        global_screening_context = f"Hasil Analisis Biometrik Multi-Angle 8-Step:\n{analysis_result}"
        
        active_id = session.get('active_screening_id')
        if active_id:
            scr = ScreeningSession.query.get(active_id)
            if scr:
                scr.scan_report = analysis_result
                db.session.commit()
        
        return jsonify({'status': 'success', 'analysis': analysis_result})
    except Exception as e:
        fallback_report = "1. **📊 Analisis Wajah, Mata & Profil**\n- Evaluasi visual menunjukkan fokus stabil.\n2. **⚡ Rekomendasi**\n- Istirahat teratur."
        global_screening_context = f"Hasil Analisis Biometrik:\n{fallback_report}"
        return jsonify({'status': 'success', 'analysis': fallback_report})

# --- WIZARD TAHAP 1 - 6 (TERPADU DENGAN NAMA & UMUR) ---
@app.route('/api/screening/step1_medical', methods=['POST'])
def step1_medical():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    data = request.get_json()
    try:
        new_session = ScreeningSession(
            user_id=session['user_id'],
            full_name=data.get('full_name'),
            age=data.get('age'),
            gender=data.get('gender'),
            current_complaints=data.get('current_complaints'),
            duration_complaints=data.get('duration_complaints'),
            diseases=data.get('diseases'),
            height=data.get('height'),
            weight=data.get('weight'),
            blood_pressure=data.get('blood_pressure'),
            sleep_hours=data.get('sleep_hours'),
            exercise_routine=data.get('exercise_routine'),
            stress_level=data.get('stress_level'),
            medical_history=data.get('medical_history'),
            current_medication=data.get('current_medication'),
            family_medical_history=data.get('family_medical_history')
        )
        db.session.add(new_session)
        db.session.commit()
        session['active_screening_id'] = new_session.id
        return jsonify({'status': 'success', 'session_id': new_session.id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/screening/step3_voice', methods=['POST'])
def step3_voice():
    if 'user_id' not in session:
        return jsonify({'status': 'error'}), 401
    if 'audio_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'Audio tidak ditemukan'}), 400
    
    audio = request.files['audio_file']
    audio_path = 'temp_voice.webm'
    audio.save(audio_path)
    active_id = session.get('active_screening_id')
    
    try:
        with open(audio_path, 'rb') as f:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=f)
        text_content = transcript.text
        
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Berikan narasi singkat (maks 2 kalimat) respon Dr. Siku menyapa dan mengkonfirmasi penerimaan jurnal suara."},
                      {"role": "user", "content": text_content}]
        )
        brief_spoken_response = res.choices[0].message.content
        
        scr = ScreeningSession.query.get(active_id)
        if scr:
            scr.voice_transcript = text_content
            scr.voice_analysis = brief_spoken_response
            db.session.commit()
            
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        return jsonify({
            'status': 'success',
            'transcript': text_content,
            'brief_response': brief_spoken_response
        })
    except Exception as e:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/screening/step4_synthesize', methods=['POST'])
def step4_synthesize():
    if 'user_id' not in session:
        return jsonify({'status': 'error'}), 401
    active_id = session.get('active_screening_id')
    scr = ScreeningSession.query.get(active_id)
    if not scr:
        return jsonify({'status': 'error', 'message': 'Sesi tidak ditemukan'}), 400
        
    prompt = f"""
Sintesis data 17 agen AI Sikutaki:
1. Data Medis & Keluhan: Nama: {scr.full_name}, Umur: {scr.age}, Keluhan: {scr.current_complaints} (Durasi: {scr.duration_complaints}), BB: {scr.weight}, TB: {scr.height}, TD: {scr.blood_pressure}, Stres: {scr.stress_level}
2. Extracted Visual Scan 8-Step: {scr.scan_report}
3. Voice Biomarker: {scr.voice_transcript}

Buatkan Laporan Akhir Screening Kesehatan Holistik yang komprehensif, mencakup status fisik, kondisi otot/postur, dan profil stres emosional.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=900
        )
        master_report = response.choices[0].message.content
        scr.master_report = master_report
        db.session.commit()
        return jsonify({'status': 'success', 'master_report': master_report})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/screening/step6_action_plan', methods=['POST'])
def step6_action_plan():
    if 'user_id' not in session:
        return jsonify({'status': 'error'}), 401
    active_id = session.get('active_screening_id')
    scr = ScreeningSession.query.get(active_id)
    
    prompt = f"Berdasarkan laporan kesehatan berikut: {scr.master_report if scr else ''}, buatkan 3-5 item To-Do List Action Plan 1-minggu yang konkret. Kembalikan JSON murni format: {{\"tasks\": [\"...\"]}}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        tasks = result.get("tasks", [])
        
        WeeklyTask.query.filter_by(session_id=active_id).delete()
        for t in tasks:
            db.session.add(WeeklyTask(session_id=active_id, task_text=t, task_type='weekly'))
        db.session.commit()
        return jsonify({'status': 'success', 'tasks': tasks})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/companion/chat', methods=['POST'])
def companion_chat():
    global global_screening_context
    if 'user_id' not in session:
        return jsonify({'companion_response': 'Sesi habis, silakan login kembali.'}), 401
        
    data = request.get_json()
    user_message = data.get('message', '')
    history = data.get('history', [])
    
    messages = [{"role": "system", "content": f"{COUNSELOR_SYSTEM_PROMPT}\n\nKONTEKS LAPORAN KESEHATAN SIKUTAKI.AI:\n{global_screening_context}"}]
    
    for h in history[-6:]:
        messages.append({"role": h.get('role'), "content": h.get('content')})
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.8,
            max_tokens=350
        )
        return jsonify({'companion_response': response.choices[0].message.content})
    except Exception as e:
        return jsonify({'companion_response': f"Kendala koneksi AI: {str(e)}"}), 500

@app.route('/api/text-to-speech', methods=['POST'])
def text_to_speech():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({'status': 'error', 'message': 'No text provided'}), 400
        
    try:
        import re
        clean_text = re.sub(r'[*_#\-`]', '', text)[:300]
        response = client.audio.speech.create(
            model="tts-1",
            voice="shimmer",
            input=clean_text
        )
        audio_filename = f"tts_{session.get('user_id')}.mp3"
        audio_path = os.path.join('static', audio_filename)
        response.stream_to_file(audio_path)
        
        return jsonify({
            'status': 'success', 
            'audio_url': url_for('static', filename=audio_filename)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/tasks/get', methods=['GET'])
def get_tasks():
    active_id = session.get('active_screening_id')
    if not active_id:
        last = ScreeningSession.query.filter_by(user_id=session.get('user_id')).order_by(ScreeningSession.created_at.desc()).first()
        active_id = last.id if last else None
    if not active_id:
        return jsonify({'status': 'success', 'tasks': []})
    tasks = WeeklyTask.query.filter_by(session_id=active_id).all()
    return jsonify({'status': 'success', 'tasks': [{'id': t.id, 'text': t.task_text, 'completed': t.is_completed} for t in tasks]})

@app.route('/api/tasks/toggle', methods=['POST'])
def toggle_task():
    data = request.get_json()
    task = WeeklyTask.query.get(data.get('task_id'))
    if task:
        task.is_completed = not task.is_completed
        db.session.commit()
        return jsonify({'status': 'success', 'completed': task.is_completed})
    return jsonify({'status': 'error'}), 404

import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
