import os
import sqlite3
import re
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, jsonify, session, Response
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kinotop-secret-key-2024'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER_POSTERS = os.path.join(BASE_DIR, 'static/uploads/posters')

os.makedirs(UPLOAD_FOLDER_POSTERS, exist_ok=True)

# ============ ADMIN PAROLI O'ZGARTIRILDI ============
ADMIN_PASSWORD = 'Betmilion1'
# ===================================================

ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# ============ VIDEO PLATFORMALARINI ANIQLASH ============
def get_video_info(url):
    """Turli platformalardan video ID va embed URL olish"""
    if not url:
        return None
    
    # YouTube
    youtube_patterns = [
        r'(?:youtu\.be\/)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]+)'
    ]
    for pattern in youtube_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return {
                'platform': 'youtube',
                'id': video_id,
                'embed_url': f'https://www.youtube.com/embed/{video_id}?autoplay=1&rel=0&modestbranding=1&showinfo=0&controls=1&fs=1',
                'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
            }
    
    # VK Video
    vk_patterns = [
        r'(?:vk\.com\/video-?\d+_\d+)',
        r'(?:vk\.com\/video_ext\.php\?oid=-?\d+&id=\d+)'
    ]
    for pattern in vk_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = url.split('/')[-1] if 'video' in url else None
            if video_id:
                parts = video_id.split('_')
                if len(parts) == 2:
                    oid, vid = parts
                    return {
                        'platform': 'vk',
                        'id': video_id,
                        'embed_url': f'https://vk.com/video_ext.php?oid={oid}&id={vid}&autoplay=1',
                        'thumbnail': None
                    }
    
    # UzMovi
    uzmovi_patterns = [
        r'(?:uzmovi\.com\/)([a-zA-Z0-9_-]+)',
        r'(?:uzmovi\.uz\/)([a-zA-Z0-9_-]+)'
    ]
    for pattern in uzmovi_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return {
                'platform': 'uzmovi',
                'id': video_id,
                'embed_url': f'https://uzmovi.com/embed/{video_id}',
                'thumbnail': None
            }
    
    # Instagram
    instagram_patterns = [
        r'(?:instagram\.com\/p\/([a-zA-Z0-9_-]+))',
        r'(?:instagr\.am\/p\/([a-zA-Z0-9_-]+))',
        r'(?:instagram\.com\/reel\/([a-zA-Z0-9_-]+))'
    ]
    for pattern in instagram_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return {
                'platform': 'instagram',
                'id': video_id,
                'embed_url': f'https://www.instagram.com/p/{video_id}/embed',
                'thumbnail': None
            }
    
    # Vimeo
    vimeo_patterns = [
        r'(?:vimeo\.com\/)(\d+)',
        r'(?:player\.vimeo\.com\/video\/)(\d+)'
    ]
    for pattern in vimeo_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return {
                'platform': 'vimeo',
                'id': video_id,
                'embed_url': f'https://player.vimeo.com/video/{video_id}?autoplay=1',
                'thumbnail': None
            }
    
    # DailyMotion
    dailymotion_patterns = [
        r'(?:dailymotion\.com\/video\/)([a-zA-Z0-9]+)',
        r'(?:dai\.ly\/)([a-zA-Z0-9]+)'
    ]
    for pattern in dailymotion_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return {
                'platform': 'dailymotion',
                'id': video_id,
                'embed_url': f'https://www.dailymotion.com/embed/video/{video_id}?autoplay=1',
                'thumbnail': None
            }
    
    return None

def get_short_info(url):
    """Shortslar uchun platforma aniqlash"""
    if not url:
        return None
    
    # YouTube Shorts
    youtube_shorts_pattern = r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]+)'
    match = re.search(youtube_shorts_pattern, url)
    if match:
        video_id = match.group(1)
        return {
            'platform': 'youtube',
            'id': video_id,
            'embed_url': f'https://www.youtube.com/embed/{video_id}?autoplay=1&rel=0&modestbranding=1&showinfo=0&controls=0&fs=0',
            'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
        }
    
    # Instagram Reels
    instagram_reel_pattern = r'(?:instagram\.com\/reel\/([a-zA-Z0-9_-]+))'
    match = re.search(instagram_reel_pattern, url)
    if match:
        video_id = match.group(1)
        return {
            'platform': 'instagram',
            'id': video_id,
            'embed_url': f'https://www.instagram.com/p/{video_id}/embed',
            'thumbnail': None
        }
    
    # TikTok
    tiktok_patterns = [
        r'(?:tiktok\.com\/@[\w]+\/video\/(\d+))',
        r'(?:tiktok\.com\/embed\/v2\/)(\d+)'
    ]
    for pattern in tiktok_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return {
                'platform': 'tiktok',
                'id': video_id,
                'embed_url': f'https://www.tiktok.com/embed/v2/{video_id}',
                'thumbnail': None
            }
    
    return get_video_info(url)

# ============ DATABASE ============
def get_db():
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
            embed_url TEXT NOT NULL,
            video_id TEXT,
            platform TEXT,
            thumbnail TEXT,
            turi TEXT DEFAULT 'url'
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS shorts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sarlavha TEXT NOT NULL,
            tafsilot TEXT,
            embed_url TEXT NOT NULL,
            video_id TEXT,
            platform TEXT,
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

# ============ API ============
@app.route('/api/check/<kod>')
def check_film(kod):
    with get_db() as conn:
        row = conn.execute("SELECT id, nomi, platform FROM films WHERE kod = ?", (kod.upper(),)).fetchone()
    
    if row:
        return jsonify({"exists": True, "nomi": row['nomi'], "platform": row['platform']}), 200
    return jsonify({"exists": False}), 404

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
    video_url = request.form.get('video_url', '').strip()
    
    if not video_url:
        return "Video URL manzili kerak!", 400
    
    video_info = get_video_info(video_url)
    if not video_info:
        return "Noto'g'ri video URL! YouTube, VK, UzMovi, Instagram, Vimeo, DailyMotion qo'llab-quvvatlanadi.", 400
    
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
                (kod, nomi, tafsilot, yil, janr, rasm, embed_url, video_id, platform, thumbnail, turi) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (kod, nomi, tafsilot, yil, janr, rasm_nomi, 
                 video_info['embed_url'], video_info.get('id'), 
                 video_info['platform'], video_info.get('thumbnail'), 'url'))
            film_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO featured_films (film_id) VALUES (?)", (film_id,))
            conn.commit()
    except sqlite3.IntegrityError:
        return "Bunday kod allaqachon mavjud!", 400
    
    return redirect(url_for('admin'))

@app.route('/admin/shorts', methods=['POST'])
def admin_add_shorts():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    sarlavha = request.form['sarlavha'].strip()
    tafsilot = request.form.get('tafsilot', '')
    video_url = request.form.get('video_url', '').strip()
    
    if not video_url:
        return "Video URL manzili kerak!", 400
    
    video_info = get_short_info(video_url)
    if not video_info:
        return "Noto'g'ri video URL! YouTube Shorts, Instagram Reel, TikTok qo'llab-quvvatlanadi.", 400
    
    with get_db() as conn:
        conn.execute("""INSERT INTO shorts 
            (sarlavha, tafsilot, embed_url, video_id, platform) 
            VALUES (?, ?, ?, ?, ?)""",
            (sarlavha, tafsilot, video_info['embed_url'], 
             video_info.get('id'), video_info['platform']))
        conn.commit()
    
    return redirect(url_for('admin'))

@app.route('/admin/film/delete/<int:id>', methods=['POST'])
def admin_delete_film(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    with get_db() as conn:
        row = conn.execute("SELECT rasm FROM films WHERE id = ?", (id,)).fetchone()
        if row and row['rasm']:
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║     🎬 KINOTOP - URL VIDEO PLATFORMASI 🎬                                ║
    ║                                                                          ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║                                                                          ║
    ║  🌐 PORT:        {}                                                       ║
    ║  🔐 ADMIN:       /admin                                                  ║
    ║  📝 ADMIN PASS:  Betmilion1                                              ║
    ║                                                                          ║
    ║  ⚡ QO'LLAB-QUVVATLANADIGAN PLATFORMALAR:                                 ║
    ║     ✓ YouTube / YouTube Shorts                                          ║
    ║     ✓ VK Video                                                          ║
    ║     ✓ UzMovi                                                            ║
    ║     ✓ Instagram / Instagram Reels                                       ║
    ║     ✓ TikTok                                                            ║
    ║     ✓ Vimeo                                                             ║
    ║     ✓ DailyMotion                                                       ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """.format(port))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
