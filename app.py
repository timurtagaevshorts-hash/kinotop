import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, session
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kinotop-secret-key')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER_FILMS = os.path.join(BASE_DIR, 'static/uploads/films')
UPLOAD_FOLDER_SHORTS = os.path.join(BASE_DIR, 'static/uploads/shorts')

os.makedirs(UPLOAD_FOLDER_FILMS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_SHORTS, exist_ok=True)

ADMIN_PASSWORD = 'Betmilion1'
ALLOWED_VIDEO = {'mp4', 'avi', 'mkv', 'mov', 'webm'}
ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif'}

# ============ DATABASE ============
def get_db():
    """Return database connection with row factory"""
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS films (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod TEXT UNIQUE NOT NULL,
            nomi TEXT NOT NULL,
            tafsilot TEXT,
            yil TEXT,
            janr TEXT,
            rasm TEXT,
            fayl_nomi TEXT NOT NULL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS shorts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sarlavha TEXT NOT NULL,
            tafsilot TEXT,
            fayl_nomi TEXT NOT NULL,
            sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ============ VIDEO STREAMING (optimized) ============
@app.route('/stream/<kod>')
def stream_video(kod):
    with get_db() as conn:
        row = conn.execute("SELECT fayl_nomi FROM films WHERE kod = ?", (kod,)).fetchone()
    
    if not row:
        return "Film topilmadi!", 404
    
    video_path = os.path.join(UPLOAD_FOLDER_FILMS, row['fayl_nomi'])
    if not os.path.exists(video_path):
        return "Video topilmadi!", 404
    
    return send_file(video_path, mimetype='video/mp4')

@app.route('/stream-shorts/<int:id>')
def stream_shorts(id):
    with get_db() as conn:
        row = conn.execute("SELECT fayl_nomi FROM shorts WHERE id = ?", (id,)).fetchone()
    
    if not row:
        return "Short topilmadi", 404
    
    video_path = os.path.join(UPLOAD_FOLDER_SHORTS, row['fayl_nomi'])
    if not os.path.exists(video_path):
        return "Video topilmadi", 404
    
    return send_file(video_path, mimetype='video/mp4')

# ============ DOWNLOAD ============
@app.route('/download/<kod>')
def download_film(kod):
    with get_db() as conn:
        row = conn.execute("SELECT fayl_nomi, nomi FROM films WHERE kod = ?", (kod,)).fetchone()
    
    if not row:
        return "Film topilmadi!", 404
    
    video_path = os.path.join(UPLOAD_FOLDER_FILMS, row['fayl_nomi'])
    return send_file(video_path, as_attachment=True, download_name=f"{row['nomi']}.mp4", mimetype='video/mp4')

# ============ API ============
@app.route('/api/check/<kod>')
def check_film(kod):
    with get_db() as conn:
        row = conn.execute("SELECT id, nomi FROM films WHERE kod = ?", (kod.upper(),)).fetchone()
    
    if row:
        return jsonify({"exists": True, "nomi": row['nomi']})
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

# ============ ADMIN AUTH ============
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('parol') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin.html', login=False, xato="Parol noto'g'ri!")
    return redirect(url_for('admin_dashboard')) if session.get('admin_logged_in') else render_template('admin.html', login=False)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

# ============ ADMIN DASHBOARD ============
@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return render_template('admin.html', login=False)
    
    with get_db() as conn:
        filmlar = [dict(row) for row in conn.execute("SELECT * FROM films ORDER BY id DESC").fetchall()]
        shorts_list = [dict(row) for row in conn.execute("SELECT * FROM shorts ORDER BY sana DESC").fetchall()]
        total_films = conn.execute("SELECT COUNT(*) as c FROM films").fetchone()['c']
        total_shorts = conn.execute("SELECT COUNT(*) as c FROM shorts").fetchone()['c']
    
    return render_template('admin.html', login=True, filmlar=filmlar, shorts_list=shorts_list,
                           total_films=total_films, total_shorts=total_shorts)

# ============ ADMIN CRUD ============
@app.route('/admin/film', methods=['POST'])
@admin_required
def admin_add_film():
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
    video_path = os.path.join(UPLOAD_FOLDER_FILMS, yangi_nom)
    fayl.save(video_path)
    
    rasm_nomi = None
    if 'rasm' in request.files:
        rasm = request.files['rasm']
        if rasm and rasm.filename and allowed_file(rasm.filename, ALLOWED_IMAGE):
            rasm_ext = rasm.filename.rsplit('.', 1)[1].lower()
            rasm_nomi = f"{kod}.{rasm_ext}"
            rasm.save(os.path.join(BASE_DIR, 'static/uploads', rasm_nomi))
    
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO films (kod, nomi, tafsilot, yil, janr, rasm, fayl_nomi) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (kod, nomi, tafsilot, yil, janr, rasm_nomi, yangi_nom))
            conn.execute("INSERT INTO featured_films (film_id) VALUES (?)", (conn.execute("SELECT last_insert_rowid()").fetchone()[0],))
            conn.commit()
    except sqlite3.IntegrityError:
        os.remove(video_path)
        return "Bunday kod allaqachon mavjud!", 400
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/shorts', methods=['POST'])
@admin_required
def admin_add_shorts():
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
    
    with get_db() as conn:
        conn.execute("INSERT INTO shorts (sarlavha, tafsilot, fayl_nomi) VALUES (?, ?, ?)",
                    (sarlavha, tafsilot, yangi_nom))
        conn.commit()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/film/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_film(id):
    with get_db() as conn:
        row = conn.execute("SELECT fayl_nomi, rasm FROM films WHERE id = ?", (id,)).fetchone()
        if row:
            fayl_path = os.path.join(UPLOAD_FOLDER_FILMS, row['fayl_nomi'])
            if os.path.exists(fayl_path):
                os.remove(fayl_path)
            if row['rasm']:
                rasm_path = os.path.join(BASE_DIR, 'static/uploads', row['rasm'])
                if os.path.exists(rasm_path):
                    os.remove(rasm_path)
            conn.execute("DELETE FROM featured_films WHERE film_id = ?", (id,))
            conn.execute("DELETE FROM films WHERE id = ?", (id,))
            conn.commit()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/shorts/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_shorts(id):
    with get_db() as conn:
        row = conn.execute("SELECT fayl_nomi FROM shorts WHERE id = ?", (id,)).fetchone()
        if row:
            fayl_path = os.path.join(UPLOAD_FOLDER_SHORTS, row['fayl_nomi'])
            if os.path.exists(fayl_path):
                os.remove(fayl_path)
            conn.execute("DELETE FROM shorts WHERE id = ?", (id,))
            conn.commit()
    
    return redirect(url_for('admin_dashboard'))

# ============ ERROR HANDLERS ============
@app.errorhandler(404)
def not_found(error):
    return "<h1>404 - Sahifa topilmadi!</h1><a href='/'>Bosh sahifaga qaytish</a>", 404

@app.errorhandler(413)
def too_large(error):
    return "Fayl hajmi juda katta! Maksimal 4GB.", 413

# ============ MAIN ============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║     🎬 KINOTOP - OPTIMIZED VERSION 🎬                        ║
    ║                                                              ║
    ╠══════════════════════════════════════════════════════════════╣
    ║                                                              ║
    ║  🌐 PORT:        {port}                                       ║
    ║  🔐 ADMIN:       /admin                                      ║
    ║  📝 ADMIN PASS:  admin123                                    ║
    ║                                                              ║
    ║  ⚡ OPTIMIZATIONS:                                            ║
    ║     ✓ Lightweight code                                       ║
    ║     ✓ Optimized database queries                             ║
    ║     ✓ Minimal memory usage                                   ║
    ║     ✓ Fast video streaming                                   ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
