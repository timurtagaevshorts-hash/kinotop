import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, jsonify, session
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kinotop-secret-key-2024')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER_FILMS'] = os.path.join(BASE_DIR, 'static/uploads/films')
app.config['UPLOAD_FOLDER_SHORTS'] = os.path.join(BASE_DIR, 'static/uploads/shorts')
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024  # 4GB

ALLOWED_VIDEO = {'mp4', 'avi', 'mkv', 'mov', 'webm', 'm4v'}
ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Papkalarni yaratish
os.makedirs(app.config['UPLOAD_FOLDER_FILMS'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_SHORTS'], exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'static/uploads'), exist_ok=True)

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

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
        size INTEGER DEFAULT 0,
        korishlar INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS shorts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sarlavha TEXT NOT NULL,
        tafsilot TEXT,
        fayl_nomi TEXT NOT NULL,
        sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        size INTEGER DEFAULT 0,
        korishlar INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS featured_films (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        film_id INTEGER,
        featured_sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Ma'lumotlar bazasi tayyor!")

init_db()

def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

# ============ VIDEO STREAMING ============
@app.route('/stream/<kod>')
def stream_video(kod):
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT fayl_nomi FROM films WHERE kod = ?", (kod,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return "Film topilmadi!", 404
    
    video_path = os.path.join(app.config['UPLOAD_FOLDER_FILMS'], row[0])
    
    if not os.path.exists(video_path):
        return "Video topilmadi!", 404
    
    return send_file(
        video_path,
        mimetype="video/mp4",
        conditional=True,
        max_age=86400
    )

@app.route('/stream-shorts/<int:id>')
def stream_shorts(id):
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT fayl_nomi FROM shorts WHERE id = ?", (id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return "Short topilmadi", 404
    
    video_path = os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], row[0])
    
    if not os.path.exists(video_path):
        return "Video topilmadi", 404
    
    return send_file(
        video_path,
        mimetype="video/mp4",
        conditional=True,
        max_age=86400
    )

# ============ DOWNLOAD ============
@app.route('/download/<kod>')
def download_film(kod):
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT fayl_nomi, nomi FROM films WHERE kod = ?", (kod,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return "Film topilmadi!", 404
    
    video_path = os.path.join(app.config['UPLOAD_FOLDER_FILMS'], row[0])
    film_nomi = row[1]
    
    if not os.path.exists(video_path):
        return "Video topilmadi!", 404
    
    return send_file(
        video_path,
        as_attachment=True,
        download_name=f"{film_nomi}.mp4",
        mimetype='video/mp4',
        conditional=True
    )

@app.route('/download-shorts/<int:id>')
def download_shorts(id):
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT fayl_nomi, sarlavha FROM shorts WHERE id = ?", (id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return "Short topilmadi!", 404
    
    video_path = os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], row[0])
    sarlavha = row[1]
    
    if not os.path.exists(video_path):
        return "Video topilmadi!", 404
    
    return send_file(
        video_path,
        as_attachment=True,
        download_name=f"{sarlavha}.mp4",
        mimetype='video/mp4',
        conditional=True
    )

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

# ============ PUBLIC ROUTES ============
@app.route('/')
def index():
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM shorts ORDER BY sana DESC LIMIT 20")
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
    
    # Ko'rishlar sonini oshirish
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("UPDATE films SET korishlar = korishlar + 1 WHERE kod = ?", (kod.upper(),))
    conn.commit()
    conn.close()
    
    film = {
        'id': row[0], 'kod': row[1], 'nomi': row[2],
        'tafsilot': row[3], 'yil': row[4], 'janr': row[5],
        'rasm': row[6], 'fayl_nomi': row[7]
    }
    return render_template('film.html', film=film)

@app.route('/shorts/<int:id>')
def shorts_view(id):
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM shorts WHERE id = ?", (id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return "Short topilmadi!", 404
    
    # Ko'rishlar sonini oshirish
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("UPDATE shorts SET korishlar = korishlar + 1 WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    short = {
        'id': row[0], 'sarlavha': row[1], 'tafsilot': row[2],
        'fayl_nomi': row[3], 'sana': row[4]
    }
    return render_template('shorts.html', short=short)

# ============ ADMIN AUTHENTICATION ============
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        parol = request.form.get('parol')
        if parol == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html', error="❌ Parol noto'g'ri!")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# ============ ADMIN DASHBOARD ============
@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM films ORDER BY id DESC")
    filmlar = [{'id': r[0], 'kod': r[1], 'nomi': r[2], 'tafsilot': r[3], 'yil': r[4], 'janr': r[5], 'rasm': r[6], 'fayl_nomi': r[7]} for r in c.fetchall()]
    c.execute("SELECT * FROM shorts ORDER BY sana DESC")
    shorts_list = [{'id': r[0], 'sarlavha': r[1], 'tafsilot': r[2], 'fayl_nomi': r[3], 'sana': r[4]} for r in c.fetchall()]
    c.execute("SELECT COUNT(*) FROM films")
    total_films = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM shorts")
    total_shorts = c.fetchone()[0]
    conn.close()
    
    return render_template('admin.html', 
                          filmlar=filmlar, 
                          shorts_list=shorts_list,
                          total_films=total_films,
                          total_shorts=total_shorts)

@app.route('/admin/film', methods=['POST'])
def admin_film():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
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
        return "Video fayl kerak!", 400
    
    ext = fayl.filename.rsplit('.', 1)[1].lower()
    yangi_nom = f"{kod}.{ext}"
    video_path = os.path.join(app.config['UPLOAD_FOLDER_FILMS'], yangi_nom)
    fayl.save(video_path)
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
        c.execute("INSERT INTO films (kod, nomi, tafsilot, yil, janr, rasm, fayl_nomi, size) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (kod, nomi, tafsilot, yil, janr, rasm_nomi, yangi_nom, file_size))
        c.execute("INSERT INTO featured_films (film_id) VALUES (?)", (c.lastrowid,))
        conn.commit()
    except sqlite3.IntegrityError:
        os.remove(video_path)
        return "Bunday kod allaqachon mavjud!", 400
    finally:
        conn.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/shorts', methods=['POST'])
def admin_shorts():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
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
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/film/delete/<int:id>', methods=['POST'])
def admin_film_delete(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT fayl_nomi, rasm FROM films WHERE id = ?", (id,))
    row = c.fetchone()
    
    if row:
        fayl_nomi, rasm = row
        fayl_path = os.path.join(app.config['UPLOAD_FOLDER_FILMS'], fayl_nomi)
        if os.path.exists(fayl_path):
            os.remove(fayl_path)
        if rasm:
            rasm_path = os.path.join(BASE_DIR, 'static/uploads', rasm)
            if os.path.exists(rasm_path):
                os.remove(rasm_path)
        c.execute("DELETE FROM featured_films WHERE film_id = ?", (id,))
        c.execute("DELETE FROM films WHERE id = ?", (id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/shorts/delete/<int:id>', methods=['POST'])
def admin_shorts_delete(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
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
    return redirect(url_for('admin_dashboard'))

# ============ ERROR HANDLERS ============
@app.errorhandler(404)
def not_found(error):
    return "<h1>404 - Sahifa topilmadi!</h1><a href='/'>Bosh sahifaga qaytish</a>", 404

@app.errorhandler(500)
def internal_error(error):
    return "<h1>500 - Server xatosi!</h1><a href='/'>Bosh sahifaga qaytish</a>", 500

# ============ STATIC FILES ============
@app.route('/static/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'static/uploads'), filename)

# ============ MAIN ============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║           🎬 KINOTOP - DIGITALOCEAN READY 🎬                             ║
    ║                                                                          ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║                                                                          ║
    ║  🌐 PORT:        {}                                                       ║
    ║  🔐 ADMIN:       /admin/login                                            ║
    ║  📝 ADMIN PASS:  admin123                                                ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """.format(port))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
