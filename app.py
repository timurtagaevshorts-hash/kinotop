import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, jsonify, session
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kinotop-secret-key'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER_FILMS'] = os.path.join(BASE_DIR, 'static/uploads/films')
app.config['UPLOAD_FOLDER_SHORTS'] = os.path.join(BASE_DIR, 'static/uploads/shorts')
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024

ALLOWED_VIDEO = {'mp4', 'avi', 'mkv', 'mov', 'webm'}
ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER_FILMS'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_SHORTS'], exist_ok=True)
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
        fayl_nomi TEXT NOT NULL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS shorts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sarlavha TEXT NOT NULL,
        tafsilot TEXT,
        fayl_nomi TEXT NOT NULL,
        sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS featured_films (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        film_id INTEGER,
        featured_sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Database ready")

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
    
    return send_file(video_path, mimetype='video/mp4')

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
    
    return send_file(video_path, mimetype='video/mp4')

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
    
    return send_file(video_path, as_attachment=True, download_name=f"{row[1]}.mp4", mimetype='video/mp4')

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
        'rasm': row[6], 'fayl_nomi': row[7]
    }
    return render_template('film.html', film=film)

# ============ ADMIN PANEL ============
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('admin_logged_in'):
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
def admin_film():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
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
        c.execute("INSERT INTO films (kod, nomi, tafsilot, yil, janr, rasm, fayl_nomi) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (kod, nomi, tafsilot, yil, janr, rasm_nomi, yangi_nom))
        film_id = c.lastrowid
        c.execute("INSERT INTO featured_films (film_id) VALUES (?)", (film_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        os.remove(video_path)
        return "Bunday kod allaqachon mavjud!", 400
    finally:
        conn.close()
    
    return redirect(url_for('admin'))

@app.route('/admin/shorts', methods=['POST'])
def admin_shorts():
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
    video_path = os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], yangi_nom)
    fayl.save(video_path)
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO shorts (sarlavha, tafsilot, fayl_nomi) VALUES (?, ?, ?)",
              (sarlavha, tafsilot, yangi_nom))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin'))

@app.route('/admin/film/delete/<int:id>', methods=['POST'])
def admin_film_delete(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT fayl_nomi, rasm FROM films WHERE id = ?", (id,))
    row = c.fetchone()
    
    if row:
        fayl_path = os.path.join(app.config['UPLOAD_FOLDER_FILMS'], row[0])
        if os.path.exists(fayl_path):
            os.remove(fayl_path)
        if row[1]:
            rasm_path = os.path.join(BASE_DIR, 'static/uploads', row[1])
            if os.path.exists(rasm_path):
                os.remove(rasm_path)
        c.execute("DELETE FROM featured_films WHERE film_id = ?", (id,))
        c.execute("DELETE FROM films WHERE id = ?", (id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/shorts/delete/<int:id>', methods=['POST'])
def admin_shorts_delete(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT fayl_nomi FROM shorts WHERE id = ?", (id,))
    row = c.fetchone()
    
    if row:
        fayl_path = os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], row[0])
        if os.path.exists(fayl_path):
            os.remove(fayl_path)
        c.execute("DELETE FROM shorts WHERE id = ?", (id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('admin'))

@app.errorhandler(404)
def not_found(error):
    return "<h1>404 - Sahifa topilmadi!</h1><a href='/'>Bosh sahifaga qaytish</a>", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Kinotop ishga tushdi! Port: {port}")
    print(f"🔐 Admin panel: /admin (parol: admin123)")
    app.run(host='0.0.0.0', port=port, debug=False)
