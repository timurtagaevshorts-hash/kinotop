import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, Response, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER_FILMS'] = os.path.join(BASE_DIR, 'static/uploads/films')
app.config['UPLOAD_FOLDER_SHORTS'] = os.path.join(BASE_DIR, 'static/uploads/shorts')

ALLOWED_VIDEO = {'mp4', 'avi', 'mkv', 'mov', 'webm'}
ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER_FILMS'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_SHORTS'], exist_ok=True)

ADMIN_PASSWORD = 'admin123'

# Database
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
    c.execute('''CREATE TABLE IF NOT EXISTS yangi_filmlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        film_id INTEGER,
        afisha_sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()
    print("✅ DB tayyor!")

init_db()

def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

# ============ STREAMING ============
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
    
    file_size = os.path.getsize(video_path)
    range_header = request.headers.get('Range', None)
    
    def generate(video_path, start, length):
        with open(video_path, "rb") as f:
            f.seek(start)
            sent = 0
            while sent < length:
                chunk = f.read(256 * 1024)
                if not chunk:
                    break
                sent += len(chunk)
                yield chunk
    
    if not range_header:
        first_chunk = 512 * 1024
        response = Response(generate(video_path, 0, min(first_chunk, file_size)), 206, mimetype="video/mp4")
        response.headers["Content-Range"] = f"bytes 0-{min(first_chunk, file_size)-1}/{file_size}"
        response.headers["Accept-Ranges"] = "bytes"
        response.headers["Content-Length"] = str(min(first_chunk, file_size))
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
    
    response = Response(generate(video_path, byte1, length), 206, mimetype="video/mp4")
    response.headers.add("Content-Range", f"bytes {byte1}-{byte1 + length - 1}/{file_size}")
    response.headers.add("Accept-Ranges", "bytes")
    response.headers.add("Content-Length", str(length))
    return response

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
    
    def generate():
        with open(video_path, "rb") as f:
            while True:
                chunk = f.read(256 * 1024)
                if not chunk:
                    break
                yield chunk
    
    response = Response(generate(), 200, mimetype="video/mp4")
    response.headers["Accept-Ranges"] = "bytes"
    return response

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
    c.execute("SELECT id FROM films WHERE kod = ?", (kod.upper(),))
    row = c.fetchone()
    conn.close()
    return jsonify({"exists": row is not None}), 200

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
    film = {'id': row[0], 'kod': row[1], 'nomi': row[2], 'tafsilot': row[3], 'yil': row[4], 'janr': row[5], 'rasm': row[6], 'fayl_nomi': row[7]}
    return render_template('film.html', film=film)

# ============ ADMIN ============
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('parol') != ADMIN_PASSWORD:
            return render_template('admin.html', login=False, xato="Parol noto'g'ri!")
        
        db_path = os.path.join(BASE_DIR, 'database.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM films ORDER BY id DESC")
        filmlar = [{'id': r[0], 'kod': r[1], 'nomi': r[2], 'tafsilot': r[3], 'yil': r[4], 'janr': r[5], 'rasm': r[6], 'fayl_nomi': r[7]} for r in c.fetchall()]
        c.execute("SELECT * FROM shorts ORDER BY sana DESC")
        shorts_list = [{'id': r[0], 'sarlavha': r[1], 'tafsilot': r[2], 'fayl_nomi': r[3], 'sana': r[4]} for r in c.fetchall()]
        conn.close()
        return render_template('admin.html', login=True, parol=ADMIN_PASSWORD, filmlar=filmlar, shorts_list=shorts_list)
    
    return render_template('admin.html', login=False)

@app.route('/admin/film', methods=['POST'])
def admin_film():
    if request.form.get('parol') != ADMIN_PASSWORD:
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
        return "Video fayl kerak!", 400
    
    ext = fayl.filename.rsplit('.', 1)[1].lower()
    yangi_nom = f"{kod}.{ext}"
    fayl.save(os.path.join(app.config['UPLOAD_FOLDER_FILMS'], yangi_nom))
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        c.execute("INSERT INTO films (kod, nomi, tafsilot, yil, janr, rasm, fayl_nomi) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (kod, nomi, tafsilot, yil, janr, None, yangi_nom))
        c.execute("INSERT INTO yangi_filmlar (film_id) VALUES (?)", (c.lastrowid,))
        conn.commit()
    except sqlite3.IntegrityError:
        return "Bunday kod allaqachon mavjud!", 400
    finally:
        conn.close()
    
    return redirect('/admin')

@app.route('/admin/shorts', methods=['POST'])
def admin_shorts():
    if request.form.get('parol') != ADMIN_PASSWORD:
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
    fayl.save(os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], yangi_nom))
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO shorts (sarlavha, tafsilot, fayl_nomi) VALUES (?, ?, ?)",
              (sarlavha, tafsilot, yangi_nom))
    conn.commit()
    conn.close()
    
    return redirect('/admin')

@app.route('/admin/film/delete/<int:id>', methods=['POST'])
def admin_film_delete(id):
    if request.form.get('parol') != ADMIN_PASSWORD:
        return "Parol xato!", 403
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT fayl_nomi FROM films WHERE id = ?", (id,))
    row = c.fetchone()
    if row:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER_FILMS'], row[0]))
        c.execute("DELETE FROM yangi_filmlar WHERE film_id = ?", (id,))
        c.execute("DELETE FROM films WHERE id = ?", (id,))
        conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/admin/shorts/delete/<int:id>', methods=['POST'])
def admin_shorts_delete(id):
    if request.form.get('parol') != ADMIN_PASSWORD:
        return "Parol xato!", 403
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT fayl_nomi FROM shorts WHERE id = ?", (id,))
    row = c.fetchone()
    if row:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], row[0]))
        c.execute("DELETE FROM shorts WHERE id = ?", (id,))
        conn.commit()
    conn.close()
    return redirect('/admin')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
