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
    created_at = db.Column(db.DateTime, default=datetime.now)  # waktu lokal server agar tanggal sesi sesuai waktu screening

class WeeklyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('screening_session.id'), nullable=False)
    task_text = db.Column(db.Text, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    task_type = db.Column(db.String(20), default='weekly')

with app.app_context():
    db.create_all()

# --- RUTE LANDING PAGE, BLOG & AUTENTIKASI ---
@app.route('/')
def landing():
    """Rute Landing Page Publik (Gaya Sikutaki.com + 17 Agen AI)"""
    return render_template('landingpage.html')

@app.route('/blog')
def blog():
    """Rute Halaman Blog Wawasan & Inspirasi Sikutaki"""
    return render_template('blog.html')

@app.route('/terapi-personal-adaptif-ai-online')
def blog_detail_adaptif_ai():
    """Rute Halaman Detail Artikel: Terapi Personal Adaptif AI Online Lebih Akurat"""
    return render_template('blog_detail.html')

@app.route('/terapi-digital-holistik')
def blog_detail_terapi_digital():
    """Rute Halaman Detail Artikel: Terapi Digital Holistik untuk Hidup Lebih Seimbang"""
    return render_template('terapi_digital.html')

@app.route('/analisis-psikologis-mental-ai-online')
def blog_detail_analisis_psikologis():
    """Rute Halaman Detail Artikel: Analisis Psikologis Mental AI Online Terbukti Akurat"""
    return render_template('analisis_psikologis.html')

@app.route('/alat-prediksi-kesehatan-kedepan')
def blog_detail_prediksi_kesehatan():
    """Rute Halaman Detail Artikel: Alat Prediksi Kesehatan Kedepan Berbasis AI"""
    return render_template('prediksi_kesehatan.html')

# --- 5 RUTE ARTIKEL BARU ---
@app.route('/terapi-personal-adaptif-online')
def blog_detail_adaptif_online():
    """Rute Halaman Detail Artikel 1: Terapi Personal Adaptif Online Lebih Fleksibel"""
    return render_template('terapi_personal_adaptif_online.html')

@app.route('/aplikasi-scan-kesehatan-holistik')
def blog_detail_scan_holistik():
    """Rute Halaman Detail Artikel 2: Aplikasi Scan Kesehatan Holistik Berbasis AI"""
    return render_template('aplikasi_scan_kesehatan_holistik.html')

@app.route('/analisis-kesehatan-mental-komprehensif')
def blog_detail_mental_komprehensif():
    """Rute Halaman Detail Artikel 3: Analisis Kesehatan Mental Komprehensif Digital"""
    return render_template('analisis_kesehatan_mental_komprehensif.html')

@app.route('/analisis-kesehatan-fisik-mental-holistik')
def blog_detail_fisik_mental_holistik():
    """Rute Halaman Detail Artikel 4: Analisis Kesehatan Fisik & Mental Holistik Modern"""
    return render_template('analisis_kesehatan_fisik_mental_holistik.html')

@app.route('/pemantauan-kesehatan-online-ai')
def blog_detail_pemantauan_online():
    """Rute Halaman Detail Artikel 5: Pemantauan Kesehatan Online AI Real-Time"""
    return render_template('pemantauan_kesehatan_online_ai.html')

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
    return redirect(url_for('landing'))

# --- HELPER: KALKULASI METRIK DARI DATA SCREENING AKTUAL ---
MONTHS_ID_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
MONTHS_ID_FULL = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

def calc_bmi(height, weight):
    """Hitung BMI dari tinggi (cm) & berat (kg). Return float atau None."""
    try:
        if height and weight:
            h_m = float(height) / 100.0
            if h_m > 0:
                return round(float(weight) / (h_m * h_m), 1)
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    return None

def bmi_category(bmi):
    if bmi is None: return None
    if bmi < 18.5: return 'underweight'
    if bmi < 25.0: return 'normal'
    if bmi < 30.0: return 'overweight'
    return 'obese'

def bp_category(bp_str):
    """Kategori tekanan darah: low / normal / elevated / high."""
    try:
        sys, dia = [int(x) for x in str(bp_str).split('/')]
        if sys < 90 or dia < 60: return 'low'
        if sys < 120 and dia < 80: return 'normal'
        if sys < 140 and dia < 90: return 'elevated'
        return 'high'
    except (ValueError, AttributeError):
        return None

def stress_int(stress_str):
    try:
        return int(float(str(stress_str)))
    except (ValueError, TypeError):
        return None

def session_flag(stress, bp_cat):
    """Flag risiko sesi: ok / warn / high berdasarkan stres & tekanan darah."""
    s = stress_int(stress)
    if (s is not None and s >= 7) or bp_cat == 'high':
        return 'high'
    if (s is not None and s >= 5) or bp_cat in ('elevated', 'low'):
        return 'warn'
    return 'ok'

def build_session_dict(scr, scan_number, has_plan):
    """Serialisasi satu sesi screening untuk template & modal JS."""
    bmi = calc_bmi(scr.height, scr.weight)
    bp_cat = bp_category(scr.blood_pressure)
    stress = stress_int(scr.stress_level)
    dt = scr.created_at
    return {
        'id': scr.id,
        'scan_number': scan_number,
        'date_short': f"{dt.day} {MONTHS_ID_SHORT[dt.month-1]} {dt.year}",
        'date_full': f"{dt.day} {MONTHS_ID_FULL[dt.month-1]} {dt.year}",
        'date_iso': dt.strftime('%Y-%m-%d'),
        'stress': stress,
        'sleep': scr.sleep_hours,
        'bp': scr.blood_pressure,
        'bp_cat': bp_cat,
        'bmi': bmi,
        'bmi_cat': bmi_category(bmi),
        'flag': session_flag(scr.stress_level, bp_cat),
        'has_plan': has_plan,
        'full_name': scr.full_name,
        'age': scr.age,
        'gender': scr.gender,
        'height': scr.height,
        'weight': scr.weight,
        'complaints': scr.current_complaints,
        'diseases': scr.diseases,
        'exercise': scr.exercise_routine,
        'master_report': scr.master_report,
        'scan_report': scr.scan_report,
    }

def calc_scores(last):
    """Skor indikatif 0-10 yang diturunkan murni dari input screening terakhir."""
    if not last:
        return None
    stress = stress_int(last['stress'])
    sleep = last['sleep']
    bmi = last['bmi']
    bp_cat = last['bp_cat']

    # Skor fisik: kombinasi BMI & durasi tidur
    bmi_score = {'normal': 10, 'overweight': 7, 'underweight': 7, 'obese': 4, None: 6}[last['bmi_cat']]
    if sleep is None:
        sleep_score = 6
    elif sleep >= 7: sleep_score = 10
    elif sleep >= 6: sleep_score = 8
    elif sleep >= 5: sleep_score = 6
    else: sleep_score = 4
    physical = round((bmi_score + sleep_score) / 2, 1)

    # Skor organ: berbasis kategori tekanan darah
    organ = {'normal': 10, 'elevated': 7, 'low': 7, 'high': 4, None: 6}[bp_cat]

    # Skor mental: invers level stres
    mental = round(10 - stress, 1) if stress is not None else 6.0

    overall = round((physical + organ + mental) / 3, 1)
    return {'overall': overall, 'physical': physical, 'organ': organ, 'mental': mental}

@app.route('/dashboard')
def index():
    """Rute Dashboard Aplikasi Utama Pengguna yang Telah Login"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']

    # Ambil seluruh sesi screening MILIK user ini saja (terbaru di atas)
    user_sessions = ScreeningSession.query.filter_by(user_id=user_id)\
        .order_by(ScreeningSession.created_at.desc()).all()
    total_scans = len(user_sessions)
    has_scanned = total_scans > 0

    # Sesi yang sudah punya action plan
    planned_ids = {t.session_id for t in WeeklyTask.query.all()}

    sessions = []
    for idx, scr in enumerate(user_sessions):
        scan_number = total_scans - idx  # scan paling awal user = #1
        sessions.append(build_session_dict(scr, scan_number, scr.id in planned_ids))

    last = sessions[0] if sessions else None
    scores = calc_scores(last)
    last_scan_date = last['date_short'] if last else None

    return render_template('index.html',
                           username=session.get('username'),
                           total_scans=total_scans,
                           last_scan_date=last_scan_date,
                           has_scanned=has_scanned,
                           sessions=sessions,
                           last=last,
                           scores=scores)

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
    global global_screening_context
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
        global_screening_context = f"Pasien: {new_session.full_name}, Keluhan Utama: {new_session.current_complaints} (Durasi: {new_session.duration_complaints})"
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
Sintesis data 17 agen AI Sikutaki berdasarkan keluhan AKTUAL pengguna berikut:
1. Data Medis & Keluhan Utama: Nama: {scr.full_name}, Umur: {scr.age}, Keluhan: {scr.current_complaints} (Durasi: {scr.duration_complaints}), Riwayat: {scr.diseases}, BB: {scr.weight}, TB: {scr.height}, TD: {scr.blood_pressure}, Stres: {scr.stress_level}
2. Extracted Visual Scan 8-Step: {scr.scan_report or 'Belum ada scan'}
3. Voice Biomarker: {scr.voice_transcript or 'Belum ada catatan suara'}

PENTING: Buatkan Laporan Akhir Screening Kesehatan Holistik yang mendalam, mencakup status fisik, kondisi organ/metabolik, dan profil stres emosional yang HANYA berfokus dan bersumber langsung dari keluhan aktual di atas. Jangan berasumsi atau mengaitkan dengan keluhan lain yang tidak diinputkan.
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
    scr = None
    if active_id:
        scr = ScreeningSession.query.get(active_id)
    if not scr:
        scr = ScreeningSession.query.filter_by(user_id=session.get('user_id')).order_by(ScreeningSession.created_at.desc()).first()
    
    if not scr:
        return jsonify({'status': 'error', 'message': 'Data skrining tidak ditemukan'}), 400
    
    prompt = f"""
Berdasarkan data skrining dan keluhan AKTUAL pengguna berikut:
- Nama: {scr.full_name}
- Keluhan Utama: {scr.current_complaints} (Durasi: {scr.duration_complaints})
- Kondisi/Penyakit: {scr.diseases}
- Laporan Master: {scr.master_report or 'Belum ada'}

PENTING: Buatkan 3-5 item To-Do List Action Plan 1-minggu yang SANGAT KONKRET dan RELEVAN HANYA dengan keluhan aktual di atas (misalnya penanganan keluhan buang air kecil, nafsu makan, kebingungan, pencernaan, atau metabolik). JANGAN membuat rencana aksi generik seperti leher pegal, cemas berlebih, atau insomnia jika tidak dikeluhkan oleh pengguna.
Kembalikan JSON murni dalam format: {{"tasks": ["..."]}}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        tasks = result.get("tasks", [])
        
        target_session_id = scr.id
        WeeklyTask.query.filter_by(session_id=target_session_id).delete()
        for t in tasks:
            db.session.add(WeeklyTask(session_id=target_session_id, task_text=t, task_type='weekly'))
        db.session.commit()
        return jsonify({'status': 'success', 'tasks': tasks})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/companion/chat', methods=['POST'])
def companion_chat():
    if 'user_id' not in session:
        return jsonify({'companion_response': 'Sesi habis, silakan login kembali.'}), 401
        
    data = request.get_json()
    user_message = data.get('message', '')
    history = data.get('history', [])
    
    user_id = session.get('user_id')
    active_id = session.get('active_screening_id')
    scr = None
    if active_id:
        scr = ScreeningSession.query.get(active_id)
    if not scr:
        scr = ScreeningSession.query.filter_by(user_id=user_id).order_by(ScreeningSession.created_at.desc()).first()
    
    screening_context_str = "Belum ada data skrining atau keluhan tercatat."
    if scr:
        screening_context_str = f"""
- Nama: {scr.full_name} (Umur: {scr.age}, Gender: {scr.gender})
- Keluhan Utama: {scr.current_complaints} (Durasi: {scr.duration_complaints})
- Riwayat Penyakit: {scr.diseases}
- Tanda Vital: BB: {scr.weight} kg, TB: {scr.height} cm, TD: {scr.blood_pressure}, Tidur: {scr.sleep_hours} jam, Stres: {scr.stress_level}
- Laporan Master Sikutaki: {scr.master_report or 'Belum ada'}
"""
    
    dynamic_counselor_prompt = f"""
{COUNSELOR_SYSTEM_PROMPT}

DATA SKRINING & KELUHAN AKTUAL PENGGUNA SAAT INI:
{screening_context_str}

INSTRUKSI UTAMA:
Berikan analisis, empati, dan saran pendampingan yang HANYA berfokus secara spesifik pada keluhan aktual pengguna di atas (misalnya keluhan sering buang air kecil, bingung, nafsu makan, pencernaan, metabolik, dll.). JANGAN berasumsi, menggeneralisasi, atau membahas keluhan standar seperti leher pegal, cemas berlebih, atau insomnia kecuali itu memang benar-benar tertulis dalam keluhan aktual pengguna. Jadilah konselor yang sangat akurat, relevan, dan empatik.
"""

    messages = [{"role": "system", "content": dynamic_counselor_prompt}]
    
    for h in history[-6:]:
        messages.append({"role": h.get('role'), "content": h.get('content')})
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=400
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

if __name__ == '__main__':
    print("🚀 Server Sikutaki.com berjalan di http://127.0.0.1:5000")
    app.run(debug=True, port=5000)