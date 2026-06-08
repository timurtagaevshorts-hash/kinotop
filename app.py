import os
import sqlite3
import re
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, jsonify, session, Response
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kinotop-secret-key-2024'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER_FILMS = os.path.join(BASE_DIR, 'static/uploads/films')
UPLOAD_FOLDER_SHORTS = os.path.join(BASE_DIR, 'static/uploads/shorts')
UPLOAD_FOLDER_POSTERS = os.path.join(BASE_DIR, 'static/uploads/posters')

os.makedirs(UPLOAD_FOLDER_FILMS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_SHORTS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_POSTERS, exist_ok=True)

ADMIN_PASSWORD = 'admin123'
ALLOWED_VIDEO = {'mp4', 'avi', 'mkv', 'mov', 'webm', 'm4v'}
ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# ============ YOUTUBE ID AJRATISH FUNKSIYASI ============
def get_youtube_id(url):
    """YouTube havolasidan video ID ni ajratib olish"""
    if not url:
        return None
    
    patterns = [
        r'(?:youtu\.be\/)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com\/v\/)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

# ============ DATABASE ============
def get_db():
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Filmlar jadvali (youtube_id qo'shilgan)
        conn.execute('''CREATE TABLE IF NOT EXISTS films (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod TEXT UNIQUE NOT NULL,
            nomi TEXT NOT NULL,
            tafsilot TEXT,
            yil TEXT,
            janr TEXT,
            rasm TEXT,
            fayl_nomi TEXT,
            youtube_id TEXT,
            size INTEGER DEFAULT 0,
            turi TEXT DEFAULT 'file'
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS shorts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sarlavha TEXT NOT NULL,
            tafsilot TEXT,
            fayl_nomi TEXT NOT NULL,
            sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            size INTEGER DEFAULT 0
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS featured_films (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            film_id INTEGER,
            featured_sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.commit()
    print("✅ Database ready")

init_db()

def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

# ============ VIDEO STREAMING (MP4 fayllar uchun) ============
@app.route('/stream/<kod>')
def stream_video(kod):
    with get_db() as conn:
        row = conn.execute("SELECT fayl_nomi, turi FROM films WHERE kod = ?", (kod,)).fetchone()
    
    if not row:
        return "Film topilmadi!", 404
    
    # Agar YouTube video bo'lsa, stream qilma
    if row['turi'] == 'youtube':
        return "YouTube video", 400
    
    video_path = os.path.join(UPLOAD_FOLDER_FILMS, row['fayl_nomi'])
    if not os.path.exists(video_path):
        return "Video topilmadi!", 404
    
    file_size = os.path.getsize(video_path)
    range_header = request.headers.get('Range', None)
    
    def generate_chunked(video_path, start, length, chunk_size=256*1024):
        with open(video_path, "rb") as f:
            f.seek(start)
            sent = 0
            while sent < length:
                chunk = f.read(min(chunk_size, length - sent))
                if not chunk:
                    break
                sent += len(chunk)
                yield chunk
    
    if not range_header:
        first_chunk = 512 * 1024
        response = Response(
            generate_chunked(video_path, 0, min(first_chunk, file_size)), 
            206, 
            mimetype="video/mp4"
        )
        response.headers["Content-Range"] = f"bytes 0-{min(first_chunk, file_size)-1}/{file_size}"
        response.headers["Accept-Ranges"] = "bytes"
        response.headers["Content-Length"] = str(min(first_chunk, file_size))
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"
        return response
    
    byte1, byte2 = 0, None
    match = range_header.replace("bytes=", "").split("-")
    if match[0]:
        byte1 = int(match[0])
    if len(match) > 1 and match[1]:
        byte2 = int(match[1])
    
    length = file_size - byte1
    if byte2 is not None:
        length = byte2 - byte1 + 1
    
    response = Response(generate_chunked(video_path, byte1, length), 206, mimetype="video/mp4")
    response.headers.add("Content-Range", f"bytes {byte1}-{byte1 + length - 1}/{file_size}")
    response.headers.add("Accept-Ranges", "bytes")
    response.headers.add("Content-Length", str(length))
    response.headers.add("Cache-Control", "no-cache")
    response.headers.add("X-Accel-Buffering", "no")
    return response

@app.route('/stream-shorts/<int:id>')
def stream_shorts(id):
    with get_db() as conn:
        row = conn.execute("SELECT fayl_nomi FROM shorts WHERE id = ?", (id,)).fetchone()
    
    if not row:
        return "Short topilmadi", 404
    
    video_path = os.path.join(UPLOAD_FOLDER_SHORTS, row['fayl_nomi'])
    if not os.path.exists(video_path):
        return "Video topilmadi", 404
    
    def generate_fast():
        with open(video_path, "rb") as f:
            while True:
                chunk = f.read(256 * 1024)
                if not chunk:
                    break
                yield chunk
    
    response = Response(generate_fast(), 200, mimetype="video/mp4")
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response

# ============ DOWNLOAD ============
@app.route('/download/<kod>')
def download_film(kod):
    with get_db() as conn:
        row = conn.execute("SELECT fayl_nomi, nomi, turi FROM films WHERE kod = ?", (kod,)).fetchone()
    
    if not row:
        return "Film topilmadi!", 404
    
    # YouTube videolarni yuklab bo'lmaydi
    if row['turi'] == 'youtube':
        return "YouTube videolarni yuklab bo'lmaydi!", 400
    
    video_path = os.path.join(UPLOAD_FOLDER_FILMS, row['fayl_nomi'])
    return send_file(video_path, as_attachment=True, download_name=f"{row['nomi']}.mp4", mimetype='video/mp4')

# ============ API ============
@app.route('/api/check/<kod>')
def check_film(kod):
    with get_db() as conn:
        row = conn.execute("SELECT id, nomi, turi FROM films WHERE kod = ?", (kod.upper(),)).fetchone()
    
    if row:
        return jsonify({"exists": True, "nomi": row['nomi'], "turi": row['turi']}), 200
    return jsonify({"exists": False}), 404

# ============ PUBLIC ROUTES ============
@app.route('/')
def index():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM shorts ORDER BY sana DESC").fetchall()
        shorts = [dict(row) for row in rows]
    return render_template('index.html', shorts=shorts)

@app.route('/film/<kod>')
def film(kod):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM films WHERE kod = ?", (kod.upper(),)).fetchone()
    
    if not row:
        return "Film topilmadi!", 404
    
    return render_template('film.html', film=dict(row))

# ============ ADMIN PANEL ============
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('admin_logged_in'):
        with get_db() as conn:
            filmlar = [dict(row) for row in conn.execute("SELECT * FROM films ORDER BY id DESC").fetchall()]
            shorts_list = [dict(row) for row in conn.execute("SELECT * FROM shorts ORDER BY sana DESC").fetchall()]
            total_films = conn.execute("SELECT COUNT(*) as c FROM films").fetchone()['c']
            total_shorts = conn.execute("SELECT COUNT(*) as c FROM shorts").fetchone()['c']
        return render_template('admin.html', login=True, filmlar=filmlar, shorts_list=shorts_list,
                               total_films=total_films, total_shorts=total_shorts)
    
    if request.method == 'POST':
        parol = request.form.get('parol')
        if parol == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('admin.html', login=False, xato="Parol noto'g'ri!")
    
    return render_template('admin.html', login=False)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin'))

@app.route('/admin/film', methods=['POST'])
def admin_add_film():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    kod = request.form['kod'].strip().upper()
    nomi = request.form['nomi'].strip()
    tafsilot = request.form.get('tafsilot', '')
    yil = request.form.get('yil', '')
    janr = request.form.get('janr', '')
    youtube_url = request.form.get('youtube_url', '').strip()
    
    youtube_id = None
    turi = 'file'
    
    # YouTube havola tekshirish
    if youtube_url:
        youtube_id = get_youtube_id(youtube_url)
        if youtube_id:
            turi = 'youtube'
        else:
            return "Noto'g'ri YouTube havola!", 400
    
    # Agar YouTube havola bo'lmasa, video fayl kerak
    if turi == 'file':
        if 'film_fayl' not in request.files:
            return "Film fayli kerak!", 400
        
        fayl = request.files['film_fayl']
        if fayl.filename == '':
            return "Fayl tanlanmagan!", 400
        
        if not allowed_file(fayl.filename, ALLOWED_VIDEO):
            return "Video fayl kerak! (mp4, avi, mkv, mov, webm)", 400
        
        ext = fayl.filename.rsplit('.', 1)[1].lower()
        yangi_nom = f"{kod}.{ext}"
        video_path = os.path.join(UPLOAD_FOLDER_FILMS, yangi_nom)
        fayl.save(video_path)
        file_size = os.path.getsize(video_path)
        fayl_nomi = yangi_nom
    else:
        # YouTube video uchun
        fayl_nomi = None
        file_size = 0
    
    # Poster rasm saqlash
    rasm_nomi = None
    if 'rasm' in request.files:
        rasm = request.files['rasm']
        if rasm and rasm.filename and allowed_file(rasm.filename, ALLOWED_IMAGE):
            rasm_ext = rasm.filename.rsplit('.', 1)[1].lower()
            rasm_nomi = f"{kod}.{rasm_ext}"
            rasm.save(os.path.join(UPLOAD_FOLDER_POSTERS, rasm_nomi))
    
    try:
        with get_db() as conn:
            conn.execute("""INSERT INTO films 
                (kod, nomi, tafsilot, yil, janr, rasm, fayl_nomi, youtube_id, size, turi) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (kod, nomi, tafsilot, yil, janr, rasm_nomi, fayl_nomi, youtube_id, file_size, turi))
            film_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO featured_films (film_id) VALUES (?)", (film_id,))
            conn.commit()
    except sqlite3.IntegrityError:
        if turi == 'file' and fayl_nomi:
            os.remove(os.path.join(UPLOAD_FOLDER_FILMS, fayl_nomi))
        return "Bunday kod allaqachon mavjud!", 400
    
    return redirect(url_for('admin'))

@app.route('/admin/shorts', methods=['POST'])
def admin_add_shorts():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
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
    video_path = os.path.join(UPLOAD_FOLDER_SHORTS, yangi_nom)
    fayl.save(video_path)
    file_size = os.path.getsize(video_path)
    
    with get_db() as conn:
        conn.execute("INSERT INTO shorts (sarlavha, tafsilot, fayl_nomi, size) VALUES (?, ?, ?, ?)",
                    (sarlavha, tafsilot, yangi_nom, file_size))
        conn.commit()
    
    return redirect(url_for('admin'))

@app.route('/admin/film/delete/<int:id>', methods=['POST'])
def admin_delete_film(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    with get_db() as conn:
        row = conn.execute("SELECT fayl_nomi, rasm, turi FROM films WHERE id = ?", (id,)).fetchone()
        if row:
            if row['turi'] == 'file' and row['fayl_nomi']:
                fayl_path = os.path.join(UPLOAD_FOLDER_FILMS, row['fayl_nomi'])
                if os.path.exists(fayl_path):
                    os.remove(fayl_path)
            if row['rasm']:
                rasm_path = os.path.join(UPLOAD_FOLDER_POSTERS, row['rasm'])
                if os.path.exists(rasm_path):
                    os.remove(rasm_path)
            conn.execute("DELETE FROM featured_films WHERE film_id = ?", (id,))
            conn.execute("DELETE FROM films WHERE id = ?", (id,))
            conn.commit()
    
    return redirect(url_for('admin'))

@app.route('/admin/shorts/delete/<int:id>', methods=['POST'])
def admin_delete_shorts(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    with get_db() as conn:
        row = conn.execute("SELECT fayl_nomi FROM shorts WHERE id = ?", (id,)).fetchone()
        if row:
            fayl_path = os.path.join(UPLOAD_FOLDER_SHORTS, row['fayl_nomi'])
            if os.path.exists(fayl_path):
                os.remove(fayl_path)
            conn.execute("DELETE FROM shorts WHERE id = ?", (id,))
            conn.commit()
    
    return redirect(url_for('admin'))

# ============ STATIC FILES ============
@app.route('/static/uploads/posters/<filename>')
def serve_poster(filename):
    return send_from_directory(UPLOAD_FOLDER_POSTERS, filename)

# ============ ERROR HANDLERS ============
@app.errorhandler(404)
def not_found(error):
    return "<h1>404 - Sahifa topilmadi!</h1><a href='/'>Bosh sahifaga qaytish</a>", 404

@app.errorhandler(413)
def too_large(error):
    return "Fayl hajmi juda katta! Maksimal 4GB.", 413

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║     🎬 KINOTOP - YOUTUBE INTEGRATION VERSION 🎬                          ║
    ║                                                                          ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║                                                                          ║
    ║  🌐 PORT:        {}                                                       ║
    ║  🔐 ADMIN:       /admin                                                  ║
    ║  📝 ADMIN PASS:  admin123                                                ║
    ║                                                                          ║
    ║  ⚡ FEATURES:                                                             ║
    ║     ✓ YouTube havola orqali video ko'rsatish                             ║
    ║     ✓ O'z video fayllarni yuklash                                        ║
    ║     ✓ Cheksiz video saqlash (YouTube orqali)                             ║
    ║     ✓ 413 xatosi YO'Q!                                                  ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """.format(port))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
