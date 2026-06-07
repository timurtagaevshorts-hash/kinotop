import os
import sqlite3
import logging
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, session, flash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import secrets

# ============ KONFIGURATSIYA ============
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Secret key
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Upload folders
app.config['UPLOAD_FOLDER_FILMS'] = os.path.join(BASE_DIR, 'static/uploads/films')
app.config['UPLOAD_FOLDER_SHORTS'] = os.path.join(BASE_DIR, 'static/uploads/shorts')
app.config['UPLOAD_FOLDER_POSTERS'] = os.path.join(BASE_DIR, 'static/uploads/posters')
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024  # 4GB
app.config['ALLOWED_VIDEO_EXTENSIONS'] = {'mp4', 'avi', 'mkv', 'mov', 'webm', 'm4v'}
app.config['ALLOWED_IMAGE_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Create folders
os.makedirs(app.config['UPLOAD_FOLDER_FILMS'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_SHORTS'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_POSTERS'], exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'static/uploads'), exist_ok=True)

# Admin password
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ HELPER FUNCTIONS ============
def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_db():
    """Database connection"""
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def admin_required(f):
    """Admin decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def format_file_size(size):
    """Format file size for display"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

# ============ DATABASE INITIALIZATION ============
def init_db():
    with get_db() as conn:
        c = conn.cursor()
        
        # Films table
        c.execute('''CREATE TABLE IF NOT EXISTS films (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod TEXT UNIQUE NOT NULL,
            nomi TEXT NOT NULL,
            tafsilot TEXT,
            yil TEXT,
            janr TEXT,
            rejissyor TEXT,
            aktyorlar TEXT,
            davomiylik INTEGER,
            rasm TEXT,
            fayl_nomi TEXT NOT NULL,
            size INTEGER DEFAULT 0,
            korishlar INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Shorts table
        c.execute('''CREATE TABLE IF NOT EXISTS shorts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sarlavha TEXT NOT NULL,
            tafsilot TEXT,
            fayl_nomi TEXT NOT NULL,
            size INTEGER DEFAULT 0,
            korishlar INTEGER DEFAULT 0,
            sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Featured films (afisha)
        c.execute('''CREATE TABLE IF NOT EXISTS featured_films (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            film_id INTEGER,
            featured_sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (film_id) REFERENCES films (id)
        )''')
        
        # Users table (for future expansion)
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.commit()
    
    logger.info("Database initialized successfully")

init_db()

# ============ VIDEO STREAMING ============
@app.route('/stream/<kod>')
def stream_video(kod):
    """Video streaming with range support"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT fayl_nomi FROM films WHERE kod = ?", (kod,))
        row = c.fetchone()
    
    if not row:
        return "Film topilmadi!", 404
    
    video_path = os.path.join(app.config['UPLOAD_FOLDER_FILMS'], row['fayl_nomi'])
    
    if not os.path.exists(video_path):
        return "Video topilmadi!", 404
    
    return send_file(
        video_path,
        mimetype="video/mp4",
        conditional=True,
        max_age=86400,
        download_name=row['fayl_nomi']
    )

@app.route('/stream-shorts/<int:id>')
def stream_shorts(id):
    """Shorts streaming"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT fayl_nomi FROM shorts WHERE id = ?", (id,))
        row = c.fetchone()
    
    if not row:
        return "Short topilmadi!", 404
    
    video_path = os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], row['fayl_nomi'])
    
    if not os.path.exists(video_path):
        return "Video topilmadi!", 404
    
    return send_file(
        video_path,
        mimetype="video/mp4",
        conditional=True,
        max_age=86400
    )

# ============ DOWNLOAD ============
@app.route('/download/<kod>')
def download_film(kod):
    """Download film"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT fayl_nomi, nomi FROM films WHERE kod = ?", (kod,))
        row = c.fetchone()
    
    if not row:
        return "Film topilmadi!", 404
    
    video_path = os.path.join(app.config['UPLOAD_FOLDER_FILMS'], row['fayl_nomi'])
    
    if not os.path.exists(video_path):
        return "Video topilmadi!", 404
    
    return send_file(
        video_path,
        as_attachment=True,
        download_name=f"{row['nomi']}.mp4",
        mimetype='video/mp4',
        conditional=True
    )

@app.route('/download-shorts/<int:id>')
def download_shorts(id):
    """Download short"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT fayl_nomi, sarlavha FROM shorts WHERE id = ?", (id,))
        row = c.fetchone()
    
    if not row:
        return "Short topilmadi!", 404
    
    video_path = os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], row['fayl_nomi'])
    
    if not os.path.exists(video_path):
        return "Video topilmadi!", 404
    
    return send_file(
        video_path,
        as_attachment=True,
        download_name=f"{row['sarlavha']}.mp4",
        mimetype='video/mp4',
        conditional=True
    )

# ============ API ENDPOINTS ============
@app.route('/api/check/<kod>')
def api_check_film(kod):
    """Check if film exists"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, nomi, yil, janr FROM films WHERE kod = ?", (kod.upper(),))
        row = c.fetchone()
    
    if row:
        return jsonify({
            "exists": True,
            "nomi": row['nomi'],
            "yil": row['yil'],
            "janr": row['janr']
        })
    return jsonify({"exists": False}), 404

@app.route('/api/films')
def api_films():
    """Get all films"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT kod, nomi, yil, janr, korishlar FROM films ORDER BY korishlar DESC LIMIT 50")
        films = [dict(row) for row in c.fetchall()]
    
    return jsonify(films)

@app.route('/api/shorts')
def api_shorts():
    """Get all shorts"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, sarlavha, korishlar FROM shorts ORDER BY korishlar DESC LIMIT 50")
        shorts = [dict(row) for row in c.fetchall()]
    
    return jsonify(shorts)

# ============ PUBLIC ROUTES ============
@app.route('/')
def index():
    """Home page"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM shorts ORDER BY sana DESC LIMIT 20")
        shorts = [dict(row) for row in c.fetchall()]
    
    return render_template('index.html', shorts=shorts)

@app.route('/film/<kod>')
def film(kod):
    """Film page"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM films WHERE kod = ?", (kod.upper(),))
        row = c.fetchone()
    
    if not row:
        return "Film topilmadi!", 404
    
    # Increment view count
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE films SET korishlar = korishlar + 1 WHERE kod = ?", (kod.upper(),))
        conn.commit()
    
    film = dict(row)
    return render_template('film.html', film=film)

@app.route('/shorts/<int:id>')
def shorts_view(id):
    """Shorts page"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM shorts WHERE id = ?", (id,))
        row = c.fetchone()
    
    if not row:
        return "Short topilmadi!", 404
    
    # Increment view count
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE shorts SET korishlar = korishlar + 1 WHERE id = ?", (id,))
        conn.commit()
    
    return render_template('shorts.html', short=dict(row))

@app.route('/search')
def search():
    """Search page"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return redirect(url_for('index'))
    
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""SELECT kod, nomi, yil, janr, rasm FROM films 
                     WHERE nomi LIKE ? OR kod LIKE ? OR janr LIKE ?
                     ORDER BY korishlar DESC LIMIT 50""",
                  (f'%{query}%', f'%{query}%', f'%{query}%'))
        results = [dict(row) for row in c.fetchall()]
    
    return render_template('search.html', results=results, query=query)

# ============ ADMIN ROUTES ============
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login"""
    if request.method == 'POST':
        if request.form.get('parol') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session.permanent = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('❌ Parol noto\'g\'ri!', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    with get_db() as conn:
        c = conn.cursor()
        
        # Films
        c.execute("SELECT * FROM films ORDER BY id DESC")
        filmlar = [dict(row) for row in c.fetchall()]
        
        # Shorts
        c.execute("SELECT * FROM shorts ORDER BY sana DESC")
        shorts_list = [dict(row) for row in c.fetchall()]
        
        # Stats
        c.execute("SELECT COUNT(*) as count FROM films")
        total_films = c.fetchone()['count']
        
        c.execute("SELECT COUNT(*) as count FROM shorts")
        total_shorts = c.fetchone()['count']
        
        c.execute("SELECT SUM(korishlar) as views FROM films")
        total_views = c.fetchone()['views'] or 0
    
    return render_template('admin.html', 
                          filmlar=filmlar, 
                          shorts_list=shorts_list,
                          total_films=total_films,
                          total_shorts=total_shorts,
                          total_views=total_views)

@app.route('/admin/film', methods=['POST'])
@admin_required
def admin_add_film():
    """Add new film"""
    kod = request.form['kod'].strip().upper()
    nomi = request.form['nomi'].strip()
    tafsilot = request.form.get('tafsilot', '')
    yil = request.form.get('yil', '')
    janr = request.form.get('janr', '')
    rejissyor = request.form.get('rejissyor', '')
    aktyorlar = request.form.get('aktyorlar', '')
    davomiylik = request.form.get('davomiylik', 0)
    
    if 'film_fayl' not in request.files:
        flash('Film fayli kerak!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    fayl = request.files['film_fayl']
    if fayl.filename == '':
        flash('Fayl tanlanmagan!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if not allowed_file(fayl.filename, app.config['ALLOWED_VIDEO_EXTENSIONS']):
        flash('Video fayl kerak! (mp4, avi, mkv, mov, webm)', 'error')
        return redirect(url_for('admin_dashboard'))
    
    ext = fayl.filename.rsplit('.', 1)[1].lower()
    yangi_nom = f"{kod}.{ext}"
    video_path = os.path.join(app.config['UPLOAD_FOLDER_FILMS'], yangi_nom)
    fayl.save(video_path)
    file_size = os.path.getsize(video_path)
    
    # Save poster image
    rasm_nomi = None
    if 'rasm' in request.files:
        rasm = request.files['rasm']
        if rasm and rasm.filename and allowed_file(rasm.filename, app.config['ALLOWED_IMAGE_EXTENSIONS']):
            rasm_ext = rasm.filename.rsplit('.', 1)[1].lower()
            rasm_nomi = f"{kod}.{rasm_ext}"
            rasm.save(os.path.join(BASE_DIR, 'static/uploads/posters', rasm_nomi))
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO films (kod, nomi, tafsilot, yil, janr, rejissyor, aktyorlar, 
                         davomiylik, rasm, fayl_nomi, size) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (kod, nomi, tafsilot, yil, janr, rejissyor, aktyorlar, 
                       davomiylik, rasm_nomi, yangi_nom, file_size))
            c.execute("INSERT INTO featured_films (film_id) VALUES (?)", (c.lastrowid,))
            conn.commit()
        
        flash(f'✅ "{nomi}" filmi muvaffaqiyatli yuklandi!', 'success')
    except sqlite3.IntegrityError:
        os.remove(video_path)
        flash('Bunday kod allaqachon mavjud!', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/shorts', methods=['POST'])
@admin_required
def admin_add_shorts():
    """Add new short"""
    sarlavha = request.form['sarlavha'].strip()
    tafsilot = request.form.get('tafsilot', '')
    
    if 'short_fayl' not in request.files:
        flash('Video fayl kerak!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    fayl = request.files['short_fayl']
    if fayl.filename == '':
        flash('Fayl tanlanmagan!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if not allowed_file(fayl.filename, app.config['ALLOWED_VIDEO_EXTENSIONS']):
        flash('Video fayl kerak!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = fayl.filename.rsplit('.', 1)[1].lower()
    yangi_nom = f"short_{timestamp}.{ext}"
    video_path = os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], yangi_nom)
    fayl.save(video_path)
    file_size = os.path.getsize(video_path)
    
    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO shorts (sarlavha, tafsilot, fayl_nomi, size) VALUES (?, ?, ?, ?)",
                  (sarlavha, tafsilot, yangi_nom, file_size))
        conn.commit()
    
    flash(f'✅ "{sarlavha}" shorts muvaffaqiyatli yuklandi!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/film/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_film(id):
    """Delete film"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT fayl_nomi, rasm FROM films WHERE id = ?", (id,))
        row = c.fetchone()
        
        if row:
            # Delete video file
            fayl_path = os.path.join(app.config['UPLOAD_FOLDER_FILMS'], row['fayl_nomi'])
            if os.path.exists(fayl_path):
                os.remove(fayl_path)
            
            # Delete poster image
            if row['rasm']:
                rasm_path = os.path.join(BASE_DIR, 'static/uploads/posters', row['rasm'])
                if os.path.exists(rasm_path):
                    os.remove(rasm_path)
            
            # Delete from database
            c.execute("DELETE FROM featured_films WHERE film_id = ?", (id,))
            c.execute("DELETE FROM films WHERE id = ?", (id,))
            conn.commit()
    
    flash('✅ Film o\'chirildi!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/shorts/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_shorts(id):
    """Delete short"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT fayl_nomi FROM shorts WHERE id = ?", (id,))
        row = c.fetchone()
        
        if row:
            fayl_path = os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], row['fayl_nomi'])
            if os.path.exists(fayl_path):
                os.remove(fayl_path)
            
            c.execute("DELETE FROM shorts WHERE id = ?", (id,))
            conn.commit()
    
    flash('✅ Shorts o\'chirildi!', 'success')
    return redirect(url_for('admin_dashboard'))

# ============ STATIC FILES ============
@app.route('/static/uploads/posters/<filename>')
def serve_poster(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'static/uploads/posters'), filename)

# ============ ERROR HANDLERS ============
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}")
    return render_template('500.html'), 500

@app.errorhandler(413)
def too_large(error):
    flash('Fayl hajmi juda katta! Maksimal 4GB.', 'error')
    return redirect(url_for('admin_dashboard'))

# ============ MAIN ============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║                 🎬 KINOTOP - PROFESSIONAL EDITION 🎬                     ║
    ║                                                                          ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║                                                                          ║
    ║  🌐 PORT:        {}                                                       ║
    ║  🔐 ADMIN:       /admin/login                                            ║
    ║  📝 ADMIN PASS:  admin123                                                ║
    ║                                                                          ║
    ║  ⚡ FEATURES:                                                            ║
    ║     ✓ Professional video streaming with range support                   ║
    ║     ✓ SQLite database with row_factory                                  ║
    ║     ✓ Session-based admin authentication                                ║
    ║     ✓ File upload with validation                                       ║
    ║     ✓ Logging and error handling                                        ║
    ║     ✓ API endpoints for JSON data                                       ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """.format(port))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
