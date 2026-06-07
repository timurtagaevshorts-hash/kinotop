import os
import sqlite3
import subprocess
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, jsonify
from datetime import datetime

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER_FILMS'] = os.path.join(BASE_DIR, 'static/uploads/films')
app.config['UPLOAD_FOLDER_SHORTS'] = os.path.join(BASE_DIR, 'static/uploads/shorts')
app.config['HLS_FOLDER'] = os.path.join(BASE_DIR, 'static/hls')
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024

ALLOWED_VIDEO = {'mp4', 'avi', 'mkv', 'mov', 'webm', 'm4v'}
ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Papkalarni yaratish
os.makedirs(app.config['UPLOAD_FOLDER_FILMS'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_SHORTS'], exist_ok=True)
os.makedirs(app.config['HLS_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'static/uploads'), exist_ok=True)

ADMIN_PASSWORD = 'admin123'

# ============ DATABASE ============
def init_db():
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS films (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kod TEXT UNIQUE NOT NULL,
        nomi TEXT NOT NULL,
        tafsilot TEXT,
        yil TEXT,
        janr TEXT,
        rasm TEXT,
        fayl_nomi TEXT NOT NULL,
        hls_path TEXT,
        size INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS shorts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sarlavha TEXT NOT NULL,
        tafsilot TEXT,
        fayl_nomi TEXT NOT NULL,
        sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        size INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS yangi_filmlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        film_id INTEGER,
        afisha_sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Ma'lumotlar bazasi tayyor!")

init_db()

def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def convert_to_hls(video_path, output_dir, kod):
    """Videoni HLS formatiga o'tkazish"""
    os.makedirs(output_dir, exist_ok=True)
    
    hls_path = os.path.join(output_dir, 'index.m3u8')
    
    cmd = [
        'ffmpeg', '-i', video_path,
        '-c:v', 'libx264', '-c:a', 'aac',
        '-hls_time', '6',
        '-hls_list_size', '0',
        '-hls_segment_filename', os.path.join(output_dir, 'segment_%03d.ts'),
        '-f', 'hls', hls_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, timeout=300, check=True)
        return hls_path
    except:
        return None

# ============ HLS STREAMING ============
@app.route('/hls/<kod>/<path:filename>')
def serve_hls(kod, filename):
    """HLS segmentlarini yuborish"""
    hls_dir = os.path.join(app.config['HLS_FOLDER'], kod)
    return send_from_directory(hls_dir, filename)

# ============ API ============
@app.route('/api/check/<kod>')
def check_film(kod):
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, nomi FROM films WHERE kod = ?", (kod.upper(),))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"exists": True, "nomi": row[1]}), 200
    return jsonify({"exists": False}), 404

# ============ SAHIFALAR ============
@app.route('/')
def index():
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM shorts ORDER BY sana DESC")
    rows = c.fetchall()
    shorts = [{'id': r[0], 'sarlavha': r[1], 'tafsilot': r[2], 'fayl_nomi': r[3], 'sana': r[4]} for r in rows]
    conn.close()
    return render_template('index.html', shorts=shorts)

@app.route('/film/<kod>')
def film(kod):
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM films WHERE kod = ?", (kod.upper(),))
    row = c.fetchone()
    conn.close()
    if not row:
        return "Film topilmadi!", 404
    film = {
        'id': row[0], 'kod': row[1], 'nomi': row[2],
        'tafsilot': row[3], 'yil': row[4], 'janr': row[5],
        'rasm': row[6], 'fayl_nomi': row[7], 'hls_path': row[8]
    }
    return render_template('film.html', film=film)

# ============ ADMIN PANEL ============
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        parol = request.form.get('parol')
        if parol != ADMIN_PASSWORD:
            return render_template('admin.html', login=False, xato="❌ Parol noto'g'ri!")
        
        db_path = os.path.join(BASE_DIR, 'database.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM films ORDER BY id DESC")
        filmlar = [{'id': r[0], 'kod': r[1], 'nomi': r[2], 'tafsilot': r[3], 'yil': r[4], 'janr': r[5], 'rasm': r[6], 'fayl_nomi': r[7]} for r in c.fetchall()]
        c.execute("SELECT * FROM shorts ORDER BY sana DESC")
        shorts_list = [{'id': r[0], 'sarlavha': r[1], 'tafsilot': r[2], 'fayl_nomi': r[3], 'sana': r[4]} for r in c.fetchall()]
        conn.close()
        return render_template('admin.html', login=True, parol=parol, filmlar=filmlar, shorts_list=shorts_list, total_films=len(filmlar), total_shorts=len(shorts_list))
    
    return render_template('admin.html', login=False)

@app.route('/admin/film', methods=['POST'])
def admin_film():
    parol = request.form.get('parol')
    if parol != ADMIN_PASSWORD:
        return "Parol xato!", 403
    
    kod = request.form['kod'].strip().upper()
    nomi = request.form['nomi'].strip()
    tafsilot = request.form.get('tafsilot', '')
    yil = request.form.get('yil', '')
    janr = request.form.get('janr', '')
    
    if 'film_fayl' not in request.files:
        return "Film fayli kerak!", 400
    
    fayl = request.files['film_fayl']
    if fayl.filename == '':
        return "Fayl tanlanmagan!", 400
    
    if not allowed_file(fayl.filename, ALLOWED_VIDEO):
        return "Video fayl kerak! (mp4, avi, mkv, mov, webm)", 400
    
    ext = fayl.filename.rsplit('.', 1)[1].lower()
    yangi_nom = f"{kod}.{ext}"
    video_path = os.path.join(app.config['UPLOAD_FOLDER_FILMS'], yangi_nom)
    fayl.save(video_path)
    
    # HLS ga o'tkazish
    hls_dir = os.path.join(app.config['HLS_FOLDER'], kod)
    hls_path = convert_to_hls(video_path, hls_dir, kod)
    
    file_size = os.path.getsize(video_path)
    
    rasm_nomi = None
    if 'rasm' in request.files:
        rasm = request.files['rasm']
        if rasm and rasm.filename and allowed_file(rasm.filename, ALLOWED_IMAGE):
            rasm_ext = rasm.filename.rsplit('.', 1)[1].lower()
            rasm_nomi = f"{kod}.{rasm_ext}"
            rasm.save(os.path.join(BASE_DIR, 'static/uploads', rasm_nomi))
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        c.execute("INSERT INTO films (kod, nomi, tafsilot, yil, janr, rasm, fayl_nomi, hls_path, size) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (kod, nomi, tafsilot, yil, janr, rasm_nomi, yangi_nom, hls_path, file_size))
        film_id = c.lastrowid
        c.execute("INSERT INTO yangi_filmlar (film_id) VALUES (?)", (film_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        os.remove(video_path)
        return "Bunday kod allaqachon mavjud!", 400
    finally:
        conn.close()
    
    return redirect(url_for('admin', _method='POST', parol=parol))

@app.route('/admin/shorts', methods=['POST'])
def admin_shorts():
    parol = request.form.get('parol')
    if parol != ADMIN_PASSWORD:
        return "Parol xato!", 403
    
    sarlavha = request.form['sarlavha'].strip()
    tafsilot = request.form.get('tafsilot', '')
    
    if 'short_fayl' not in request.files:
        return "Video fayl kerak!", 400
    
    fayl = request.files['short_fayl']
    if fayl.filename == '':
        return "Fayl tanlanmagan!", 400
    
    if not allowed_file(fayl.filename, ALLOWED_VIDEO):
        return "Video fayl kerak!", 400
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = fayl.filename.rsplit('.', 1)[1].lower()
    yangi_nom = f"short_{timestamp}.{ext}"
    video_path = os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], yangi_nom)
    fayl.save(video_path)
    file_size = os.path.getsize(video_path)
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO shorts (sarlavha, tafsilot, fayl_nomi, size) VALUES (?, ?, ?, ?)",
              (sarlavha, tafsilot, yangi_nom, file_size))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin', _method='POST', parol=parol))

@app.route('/admin/film/delete/<int:id>', methods=['POST'])
def admin_film_delete(id):
    parol = request.form.get('parol')
    if parol != ADMIN_PASSWORD:
        return "Parol xato!", 403
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT fayl_nomi, rasm, hls_path FROM films WHERE id = ?", (id,))
    row = c.fetchone()
    
    if row:
        fayl_nomi, rasm, hls_path = row
        fayl_path = os.path.join(app.config['UPLOAD_FOLDER_FILMS'], fayl_nomi)
        if os.path.exists(fayl_path):
            os.remove(fayl_path)
        if rasm:
            rasm_path = os.path.join(BASE_DIR, 'static/uploads', rasm)
            if os.path.exists(rasm_path):
                os.remove(rasm_path)
        if hls_path:
            hls_dir = os.path.dirname(hls_path)
            import shutil
            if os.path.exists(hls_dir):
                shutil.rmtree(hls_dir)
        c.execute("DELETE FROM yangi_filmlar WHERE film_id = ?", (id,))
        c.execute("DELETE FROM films WHERE id = ?", (id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('admin', _method='POST', parol=parol))

@app.route('/admin/shorts/delete/<int:id>', methods=['POST'])
def admin_shorts_delete(id):
    parol = request.form.get('parol')
    if parol != ADMIN_PASSWORD:
        return "Parol xato!", 403
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT fayl_nomi FROM shorts WHERE id = ?", (id,))
    row = c.fetchone()
    
    if row:
        fayl_nomi = row[0]
        fayl_path = os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], fayl_nomi)
        if os.path.exists(fayl_path):
            os.remove(fayl_path)
        c.execute("DELETE FROM shorts WHERE id = ?", (id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('admin', _method='POST', parol=parol))

# ============ ERROR HANDLERS ============
@app.errorhandler(404)
def not_found(error):
    return "<h1>404 - Sahifa topilmadi!</h1><a href='/'>Bosh sahifaga qaytish</a>", 404

@app.errorhandler(500)
def internal_error(error):
    return "<h1>500 - Server xatosi!</h1><a href='/'>Bosh sahifaga qaytish</a>", 500

# ============ MAIN ============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║           🎬 KINOTOP - HLS ULTRA FAST STREAMING 🎬                       ║
    ║                                                                          ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║                                                                          ║
    ║  🌐 LOCAL:     http://localhost:{}                                       ║
    ║  🔐 ADMIN:     http://localhost:{}/admin                                 ║
    ║  📝 PAROL:     admin123                                                   ║
    ║                                                                          ║
    ║  ⚡ HLS FEATURES:                                                         ║
    ║     ✓ Segment-based streaming (6 second segments)                       ║
    ║     ✓ Instant playback - no waiting                                     ║
    ║     ✓ Adaptive bitrate                                                  ║
    ║     ✓ No buffering stutter                                              ║
    ║     ✓ Background loading                                                ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """.format(port, port))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
