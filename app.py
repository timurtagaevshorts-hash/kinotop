import os
import sqlite3
import re
import requests
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, jsonify, session, Response
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kinotop-secret-key-2024'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER_POSTERS = os.path.join(BASE_DIR, 'static/uploads/posters')

os.makedirs(UPLOAD_FOLDER_POSTERS, exist_ok=True)

# ============ ADMIN PAROLI ============
ADMIN_PASSWORD = 'Betmilion1'
# ======================================

ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# ============ VIDEO PLATFORMALARINI ANIQLASH (KENGAYTIRILGAN) ============

def extract_google_drive_id(url):
    """Google Drive dan fayl ID olish"""
    patterns = [
        r'(?:drive\.google\.com\/file\/d\/)([a-zA-Z0-9_-]+)',
        r'(?:drive\.google\.com\/open\?id=)([a-zA-Z0-9_-]+)',
        r'(?:drive\.google\.com\/uc\?id=)([a-zA-Z0-9_-]+)',
        r'(?:drive\.google\.com\/drive\/folders\/)([a-zA-Z0-9_-]+)',
        r'^([a-zA-Z0-9_-]{28,})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_google_drive_embed_url(file_id, folder=False):
    """Google Drive embed URL yaratish"""
    if folder:
        return f'https://drive.google.com/embeddedfolderview?id={file_id}#list'
    return f'https://drive.google.com/file/d/{file_id}/preview'

def extract_uzmedia_info(url):
    """Uzmedia.tv dan video ma'lumot olish"""
    # Uzmedia embed yoki to'g'ridan-to'g'ri fayl manzili
    if 'uzmedia.tv' in url:
        # Agar embed.html bo'lsa
        if 'embed.html' in url:
            return {
                'platform': 'uzmedia',
                'embed_url': url,
                'thumbnail': None
            }
        # Agar to'g'ridan-to'g'ri fayl bo'lsa
        elif 'files.uzmedia.tv' in url or '.mp4' in url:
            return {
                'platform': 'uzmedia',
                'embed_url': f'https://uzmedia.tv/embed.html?file={url}',
                'thumbnail': None
            }
        # Agar film sahifasi bo'lsa
        else:
            # Film ID ni olishga harakat qilish
            match = re.search(r'/(\d+)-', url)
            if match:
                film_id = match.group(1)
                return {
                    'platform': 'uzmedia',
                    'embed_url': f'https://uzmedia.tv/embed/{film_id}',
                    'thumbnail': None
                }
    return None

def get_video_info(url):
    """Turli platformalardan video ID va embed URL olish (Kengaytirilgan)"""
    if not url:
        return None
    
    # ===== GOOGLE DRIVE =====
    gd_id = extract_google_drive_id(url)
    if gd_id:
        return {
            'platform': 'googledrive',
            'id': gd_id,
            'embed_url': get_google_drive_embed_url(gd_id),
            'thumbnail': None,
            'direct_url': f'https://drive.google.com/uc?export=download&id={gd_id}'
        }
    
    # ===== UZMEDIA.TV =====
    uzmedia_info = extract_uzmedia_info(url)
    if uzmedia_info:
        return uzmedia_info
    
    # ===== YOUTUBE =====
    youtube_patterns = [
        r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/live\/)([a-zA-Z0-9_-]{11})'
    ]
    for pattern in youtube_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return {
                'platform': 'youtube',
                'id': video_id,
                'embed_url': f'https://www.youtube.com/embed/{video_id}?autoplay=1&rel=0&modestbranding=1&showinfo=0&controls=1&fs=1&playsinline=1',
                'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
            }
    
    # ===== VK VIDEO =====
    vk_patterns = [
        r'(?:vk\.com\/video-?\d+_\d+)',
        r'(?:vk\.com\/video_ext\.php\?oid=-?\d+&id=\d+)',
        r'(?:vk\.com\/clip-?\d+_\d+)'
    ]
    for pattern in vk_patterns:
        match = re.search(pattern, url)
        if match:
            # VK video ID ni olish
            if 'video_ext' in url:
                oid_match = re.search(r'oid=(-?\d+)', url)
                id_match = re.search(r'id=(\d+)', url)
                if oid_match and id_match:
                    return {
                        'platform': 'vk',
                        'embed_url': f'https://vk.com/video_ext.php?oid={oid_match.group(1)}&id={id_match.group(1)}&autoplay=1',
                        'thumbnail': None
                    }
            else:
                parts = url.split('/')[-1].split('_')
                if len(parts) >= 2:
                    return {
                        'platform': 'vk',
                        'embed_url': f'https://vk.com/video_ext.php?oid={parts[0]}&id={parts[1]}&autoplay=1',
                        'thumbnail': None
                    }
    
    # ===== UZMOVI / UZMOVI.UZ =====
    uzmovi_patterns = [
        r'(?:uzmovi\.com\/)([a-zA-Z0-9_-]+)',
        r'(?:uzmovi\.uz\/)([a-zA-Z0-9_-]+)',
        r'(?:uzmovi\.com\/embed\/)([a-zA-Z0-9_-]+)'
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
    
    # ===== INSTAGRAM =====
    instagram_patterns = [
        r'(?:instagram\.com\/p\/([a-zA-Z0-9_-]+))',
        r'(?:instagr\.am\/p\/([a-zA-Z0-9_-]+))',
        r'(?:instagram\.com\/reel\/([a-zA-Z0-9_-]+))',
        r'(?:instagram\.com\/tv\/([a-zA-Z0-9_-]+))'
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
    
    # ===== TIKTOK =====
    tiktok_patterns = [
        r'(?:tiktok\.com\/@[\w]+\/video\/(\d+))',
        r'(?:tiktok\.com\/embed\/v2\/)(\d+)',
        r'(?:tiktok\.com\/t\/([a-zA-Z0-9_-]+))'
    ]
    for pattern in tiktok_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1) if match.group(1) else match.group(0)
            return {
                'platform': 'tiktok',
                'id': video_id,
                'embed_url': f'https://www.tiktok.com/embed/v2/{video_id}',
                'thumbnail': None
            }
    
    # ===== VIMEO =====
    vimeo_patterns = [
        r'(?:vimeo\.com\/)(\d+)',
        r'(?:player\.vimeo\.com\/video\/)(\d+)',
        r'(?:vimeo\.com\/channels\/[\w]+\/)(\d+)'
    ]
    for pattern in vimeo_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1) if match.group(1) else match.group(0)
            return {
                'platform': 'vimeo',
                'id': video_id,
                'embed_url': f'https://player.vimeo.com/video/{video_id}?autoplay=1&playsinline=1',
                'thumbnail': None
            }
    
    # ===== DAILYMOTION =====
    dailymotion_patterns = [
        r'(?:dailymotion\.com\/video\/)([a-zA-Z0-9]+)',
        r'(?:dai\.ly\/)([a-zA-Z0-9]+)',
        r'(?:dailymotion\.com\/embed\/video\/)([a-zA-Z0-9]+)'
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
    
    # ===== MP4 / DIRECT VIDEO URL =====
    if url.endswith('.mp4') or url.endswith('.webm') or url.endswith('.ogg') or 'video' in url:
        return {
            'platform': 'direct',
            'embed_url': url,
            'thumbnail': None,
            'direct_url': url
        }
    
    return None

def get_short_info(url):
    """Shortslar uchun platforma aniqlash"""
    if not url:
        return None
    
    # YouTube Shorts
    youtube_shorts_pattern = r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})'
    match = re.search(youtube_shorts_pattern, url)
    if match:
        video_id = match.group(1)
        return {
            'platform': 'youtube',
            'id': video_id,
            'embed_url': f'https://www.youtube.com/embed/{video_id}?autoplay=1&rel=0&modestbranding=1&showinfo=0&controls=0&fs=0&playsinline=1',
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
    
    # Google Drive Shorts
    gd_id = extract_google_drive_id(url)
    if gd_id:
        return {
            'platform': 'googledrive',
            'id': gd_id,
            'embed_url': get_google_drive_embed_url(gd_id),
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
            turi TEXT DEFAULT 'url',
            direct_url TEXT
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS shorts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sarlavha TEXT NOT NULL,
            tafsilot TEXT,
            embed_url TEXT NOT NULL,
            video_id TEXT,
            platform TEXT,
            sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            direct_url TEXT
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS featured_films (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            film_id INTEGER,
            featured_sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Mavjud jadvallarga yangi ustun qo'shish (agar mavjud bo'lmasa)
        try:
            conn.execute("ALTER TABLE films ADD COLUMN direct_url TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE shorts ADD COLUMN direct_url TEXT")
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
    print("✅ Database ready")

init_db()

def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

# ============ PUBLIC ROUTES ============
@app.route('/')
def index():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM shorts ORDER BY sana DESC LIMIT 20").fetchall()
        shorts = [dict(row) for row in rows]
        featured = conn.execute("""
            SELECT f.* FROM films f 
            JOIN featured_films ff ON f.id = ff.film_id 
            ORDER BY ff.featured_sana DESC LIMIT 10
        """).fetchall()
        featured_films = [dict(row) for row in featured]
    return render_template('index.html', shorts=shorts, featured_films=featured_films)

@app.route('/film/<kod>')
def film(kod):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM films WHERE kod = ?", (kod.upper(),)).fetchone()
    
    if not row:
        return "Film topilmadi!", 404
    
    film_data = dict(row)
    
    # Qo'shimcha embed URL tayyorlash
    if film_data['platform'] == 'googledrive' and film_data.get('video_id'):
        film_data['embed_url'] = get_google_drive_embed_url(film_data['video_id'])
    elif film_data['platform'] == 'direct' and film_data.get('direct_url'):
        film_data['embed_url'] = film_data['direct_url']
    
    return render_template('film.html', film=film_data)

@app.route('/shorts')
def shorts():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM shorts ORDER BY sana DESC").fetchall()
        shorts_list = [dict(row) for row in rows]
    return render_template('shorts.html', shorts=shorts_list)

@app.route('/filmlar')
def filmlar():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM films ORDER BY id DESC").fetchall()
        filmlar_list = [dict(row) for row in rows]
    return render_template('filmlar.html', filmlar=filmlar_list)

# ============ API ============
@app.route('/api/check/<kod>')
def check_film(kod):
    with get_db() as conn:
        row = conn.execute("SELECT id, nomi, platform FROM films WHERE kod = ?", (kod.upper(),)).fetchone()
    
    if row:
        return jsonify({"exists": True, "nomi": row['nomi'], "platform": row['platform']}), 200
    return jsonify({"exists": False}), 404

@app.route('/api/platforms')
def get_platforms():
    """Qo'llab-quvvatlanadigan platformalar ro'yxati"""
    platforms = [
        {'name': 'YouTube', 'icon': 'fab fa-youtube', 'color': '#FF0000'},
        {'name': 'Google Drive', 'icon': 'fab fa-google-drive', 'color': '#4285F4'},
        {'name': 'Uzmedia.tv', 'icon': 'fas fa-tv', 'color': '#667eea'},
        {'name': 'VK Video', 'icon': 'fab fa-vk', 'color': '#4680C2'},
        {'name': 'Instagram', 'icon': 'fab fa-instagram', 'color': '#E4405F'},
        {'name': 'TikTok', 'icon': 'fab fa-tiktok', 'color': '#000000'},
        {'name': 'Vimeo', 'icon': 'fab fa-vimeo', 'color': '#1AB7EA'},
        {'name': 'DailyMotion', 'icon': 'fab fa-dailymotion', 'color': '#0066DC'},
        {'name': 'UzMovi', 'icon': 'fas fa-film', 'color': '#00A884'},
        {'name': 'Direct MP4', 'icon': 'fas fa-video', 'color': '#28a745'}
    ]
    return jsonify(platforms)

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
        return "Noto'g'ri video URL! YouTube, Google Drive, Uzmedia.tv, VK, UzMovi, Instagram, TikTok, Vimeo, DailyMotion qo'llab-quvvatlanadi.", 400
    
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
                (kod, nomi, tafsilot, yil, janr, rasm, embed_url, video_id, platform, thumbnail, turi, direct_url) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (kod, nomi, tafsilot, yil, janr, rasm_nomi, 
                 video_info['embed_url'], video_info.get('id'), 
                 video_info['platform'], video_info.get('thumbnail'), 
                 'url', video_info.get('direct_url')))
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
        return "Noto'g'ri video URL! YouTube Shorts, Instagram Reel, TikTok, Google Drive qo'llab-quvvatlanadi.", 400
    
    with get_db() as conn:
        conn.execute("""INSERT INTO shorts 
            (sarlavha, tafsilot, embed_url, video_id, platform, direct_url) 
            VALUES (?, ?, ?, ?, ?, ?)""",
            (sarlavha, tafsilot, video_info['embed_url'], 
             video_info.get('id'), video_info['platform'], 
             video_info.get('direct_url')))
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

@app.route('/admin/featured/<int:film_id>', methods=['POST'])
def admin_toggle_featured(film_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM featured_films WHERE film_id = ?", (film_id,)).fetchone()
        if existing:
            conn.execute("DELETE FROM featured_films WHERE film_id = ?", (film_id,))
        else:
            conn.execute("INSERT INTO featured_films (film_id) VALUES (?)", (film_id,))
        conn.commit()
    
    return redirect(url_for('admin'))

# ============ STATIC FILES ============
@app.route('/static/uploads/posters/<filename>')
def serve_poster(filename):
    return send_from_directory(UPLOAD_FOLDER_POSTERS, filename)

# ============ ERROR HANDLERS ============
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║     🎬 KINOTOP - UNIVERSAL VIDEO PLATFORMASI 🎬                          ║
    ║                                                                          ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║                                                                          ║
    ║  🌐 PORT:        {}                                                       ║
    ║  🔐 ADMIN:       /admin                                                  ║
    ║  📝 ADMIN PASS:  Betmilion1                                              ║
    ║                                                                          ║
    ║  ⚡ QO'LLAB-QUVVATLANADIGAN PLATFORMALAR:                                 ║
    ║     ✓ YouTube / YouTube Shorts                                          ║
    ║     ✓ Google Drive (Video & Folder)                                     ║
    ║     ✓ Uzmedia.tv (Embed & Direct)                                       ║
    ║     ✓ VK Video / VK Clips                                               ║
    ║     ✓ UzMovi / UzMovi.uz                                                ║
    ║     ✓ Instagram / Instagram Reels                                       ║
    ║     ✓ TikTok                                                            ║
    ║     ✓ Vimeo                                                             ║
    ║     ✓ DailyMotion                                                       ║
    ║     ✓ Direct MP4 / WebM / OGG                                           ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """.format(port))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
