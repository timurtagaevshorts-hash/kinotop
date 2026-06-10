import os
import sqlite3
import re
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kinotop-secret-key-2024'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER_POSTERS = os.path.join(BASE_DIR, 'static/uploads/posters')
os.makedirs(UPLOAD_FOLDER_POSTERS, exist_ok=True)

ADMIN_PASSWORD = 'Betmilion1'
ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

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
            video_url TEXT NOT NULL,
            platform TEXT,
            sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
        # Yangi: Dinamik tugma sozlamalari uchun jadval
        conn.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Default tugma sozlamalarini qo'shish (agar mavjud bo'lmasa)
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('action_button_enabled', 'true')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('action_button_text', 'Top Kino')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('action_button_url', 'https://t.me/Kodlikino_topbot')")
        
        conn.commit()
    print("✅ Database ready")

init_db()

def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

# ============ URL NI TO'G'RI FORMATGA KELTIRISH ============
def get_redirect_url(video_url):
    """Google Drive va UZMedia uchun to'g'ri ochiladigan URL qaytaradi"""
    if not video_url:
        return video_url
    
    # Google Drive - preview sahifasiga o'tkazish
    if 'drive.google.com' in video_url:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', video_url)
        if match:
            file_id = match.group(1)
            return f'https://drive.google.com/file/d/{file_id}/preview'
        return video_url
    
    # UZMedia - embed versiyaga o'tkazish
    if 'uzmedia.tv' in video_url:
        if 'embed.html' not in video_url:
            match = re.search(r'/([a-zA-Z0-9_-]+)$', video_url)
            if match:
                video_id = match.group(1)
                return f'http://uzmedia.tv/embed.html?file={video_id}'
        return video_url
    
    return video_url

# ============ PUBLIC ROUTES ============
@app.route('/')
def index():
    with get_db() as conn:
        shorts = conn.execute("SELECT * FROM shorts ORDER BY sana DESC").fetchall()
        shorts = [dict(row) for row in shorts]
    
    return render_template('index.html', shorts=shorts)

@app.route('/film/<kod>')
def film_page(kod):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM films WHERE kod = ?", (kod.upper(),)).fetchone()
    
    if not row:
        return "Film topilmadi!", 404
    
    film = dict(row)
    video_url = film['video_url']
    redirect_url = get_redirect_url(video_url)
    
    return redirect(redirect_url)

# ============ API ============
@app.route('/api/check/<kod>')
def check_film(kod):
    with get_db() as conn:
        row = conn.execute("SELECT id, nomi FROM films WHERE kod = ?", (kod.upper(),)).fetchone()
    
    if row:
        return jsonify({"exists": True, "nomi": row['nomi']}), 200
    return jsonify({"exists": False}), 404

# ============ DINAMIK TUGMA API ============
@app.route('/api/action-button', methods=['GET'])
def get_action_button():
    """Dinamik tugma sozlamalarini olish"""
    with get_db() as conn:
        enabled = conn.execute("SELECT value FROM settings WHERE key = 'action_button_enabled'").fetchone()
        text = conn.execute("SELECT value FROM settings WHERE key = 'action_button_text'").fetchone()
        url = conn.execute("SELECT value FROM settings WHERE key = 'action_button_url'").fetchone()
    
    return jsonify({
        "enabled": enabled['value'] == 'true' if enabled else True,
        "text": text['value'] if text else "Top Kino",
        "url": url['value'] if url else "https://t.me/Kodlikino_topbot"
    })

@app.route('/api/action-button', methods=['POST'])
def update_action_button():
    """Admin panel orqali dinamik tugma sozlamalarini yangilash"""
    if not session.get('admin_logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    
    with get_db() as conn:
        if 'enabled' in data:
            conn.execute("UPDATE settings SET value = ? WHERE key = 'action_button_enabled'", 
                        ('true' if data['enabled'] else 'false',))
        if 'text' in data and data['text']:
            conn.execute("UPDATE settings SET value = ? WHERE key = 'action_button_text'", (data['text'],))
        if 'url' in data and data['url']:
            conn.execute("UPDATE settings SET value = ? WHERE key = 'action_button_url'", (data['url'],))
        conn.commit()
    
    return jsonify({"success": True})

# ============ ADMIN PANEL ============
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('admin_logged_in'):
        with get_db() as conn:
            filmlar = [dict(row) for row in conn.execute("SELECT * FROM films ORDER BY id DESC").fetchall()]
            shorts_list = [dict(row) for row in conn.execute("SELECT * FROM shorts ORDER BY sana DESC").fetchall()]
            
            # Dinamik tugma sozlamalarini olish
            action_enabled = conn.execute("SELECT value FROM settings WHERE key = 'action_button_enabled'").fetchone()
            action_text = conn.execute("SELECT value FROM settings WHERE key = 'action_button_text'").fetchone()
            action_url = conn.execute("SELECT value FROM settings WHERE key = 'action_button_url'").fetchone()
            
            total_films = len(filmlar)
            total_shorts = len(shorts_list)
            
            action_config = {
                'enabled': action_enabled['value'] == 'true' if action_enabled else True,
                'text': action_text['value'] if action_text else "Top Kino",
                'url': action_url['value'] if action_url else "https://t.me/Kodlikino_topbot"
            }
        
        return render_template('admin.html', login=True, filmlar=filmlar, shorts_list=shorts_list,
                               total_films=total_films, total_shorts=total_shorts, action_config=action_config)
    
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
    
    platform = 'other'
    if 'youtube.com' in video_url or 'youtu.be' in video_url:
        platform = 'youtube'
    elif 'drive.google.com' in video_url:
        platform = 'googledrive'
    elif 'uzmedia.tv' in video_url:
        platform = 'uzmedia'
    
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
                (kod, nomi, tafsilot, yil, janr, rasm, video_url, platform) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (kod, nomi, tafsilot, yil, janr, rasm_nomi, video_url, platform))
            conn.commit()
    except sqlite3.IntegrityError:
        return "Bunday kod allaqachon mavjud!", 400
    
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
        conn.execute("DELETE FROM films WHERE id = ?", (id,))
        conn.commit()
    
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
    
    platform = 'other'
    if 'youtube.com' in video_url or 'youtu.be' in video_url:
        platform = 'youtube'
    elif 'instagram.com' in video_url:
        platform = 'instagram'
    elif 'tiktok.com' in video_url:
        platform = 'tiktok'
    
    embed_url = video_url
    if 'youtube.com/shorts' in video_url:
        match = re.search(r'shorts/([a-zA-Z0-9_-]+)', video_url)
        if match:
            embed_url = f'https://www.youtube.com/embed/{match.group(1)}?autoplay=1'
    
    with get_db() as conn:
        conn.execute("""INSERT INTO shorts 
            (sarlavha, tafsilot, embed_url, video_id, platform) 
            VALUES (?, ?, ?, ?, ?)""",
            (sarlavha, tafsilot, embed_url, video_url, platform))
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

@app.route('/admin/action-button', methods=['POST'])
def admin_update_action_button():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    enabled = request.form.get('enabled') == 'true'
    text = request.form.get('text', 'Top Kino').strip()
    url = request.form.get('url', 'https://t.me/Kodlikino_topbot').strip()
    
    with get_db() as conn:
        conn.execute("UPDATE settings SET value = ? WHERE key = 'action_button_enabled'", ('true' if enabled else 'false',))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'action_button_text'", (text,))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'action_button_url'", (url,))
        conn.commit()
    
    return redirect(url_for('admin'))

@app.route('/static/uploads/posters/<filename>')
def serve_poster(filename):
    from flask import send_from_directory
    return send_from_directory(UPLOAD_FOLDER_POSTERS, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║     🎬 KINOTOP - REDIRECT VERSION 🎬                        ║
    ║                                                              ║
    ╠══════════════════════════════════════════════════════════════╣
    ║                                                              ║
    ║  🌐 PORT:        {port}                                      ║
    ║  🔐 ADMIN:       /admin                                     ║
    ║  📝 ADMIN PASS:  Betmilion1                                 ║
    ║                                                              ║
    ║  🎮 DINAMIK TUGMA:                                          ║
    ║     Admin panel -> "Dinamik Tugma" bo'limida sozlash        ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=port, debug=True)
