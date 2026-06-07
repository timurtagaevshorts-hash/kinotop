import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, Response, jsonify, stream_with_context
from datetime import datetime

app = Flask(__name__)

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

# ============ ULTRA TEZ SHORTS STREAMING (Range + Small Chunks) ============
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

    file_size = os.path.getsize(video_path)
    range_header = request.headers.get('Range', None)

    def generate_chunked(video_path, start, length, chunk_size=256*1024):
        """256KB chunk - silliq o'ynatish uchun"""
        with open(video_path, "rb") as f:
            f.seek(start)
            bytes_sent = 0
            while bytes_sent < length:
                chunk = f.read(min(chunk_size, length - bytes_sent))
                if not chunk:
                    break
                bytes_sent += len(chunk)
                yield chunk

    if not range_header:
        # Birinchi yuklash - faqat 1MB yuborish (darhol boshlanadi)
        first_chunk_size = min(1024 * 1024, file_size)
        response = Response(
            generate_chunked(video_path, 0, first_chunk_size),
            206,
            mimetype="video/mp4"
        )
        response.headers["Content-Range"] = f"bytes 0-{first_chunk_size - 1}/{file_size}"
        response.headers["Accept-Ranges"] = "bytes"
        response.headers["Content-Length"] = str(first_chunk_size)
        response.headers["Cache-Control"] = "public, max-age=31536000"
        return response

    # Range qo'llab-quvvatlash (oldinga/orqaga o'tish)
    byte1, byte2 = 0, None
    match = range_header.replace("bytes=", "").split("-")

    if match[0]:
        byte1 = int(match[0])

    if len(match) > 1 and match[1]:
        byte2 = int(match[1])

    length = file_size - byte1
    if byte2 is not None:
        length = byte2 - byte1 + 1

    # Chunklangan streaming
    response = Response(
        generate_chunked(video_path, byte1, length),
        206,
        mimetype="video/mp4"
    )

    response.headers.add(
        "Content-Range",
        f"bytes {byte1}-{byte1 + length - 1}/{file_size}"
    )
    response.headers.add("Accept-Ranges", "bytes")
    response.headers.add("Content-Length", str(length))
    response.headers.add("Cache-Control", "public, max-age=31536000")

    return response

# ============ ULTRA TEZ FILM STREAMING (QOTISH YO'Q) ============
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

    def generate_chunked_film(video_path, start, length, chunk_size=512*1024):
        """512KB chunk - film uchun optimal"""
        with open(video_path, "rb") as f:
            f.seek(start)
            bytes_sent = 0
            while bytes_sent < length:
                chunk = f.read(min(chunk_size, length - bytes_sent))
                if not chunk:
                    break
                bytes_sent += len(chunk)
                yield chunk

    if not range_header:
        # Birinchi yuklash - faqat 2MB yuborish (darhol boshlanadi)
        first_chunk_size = min(2 * 1024 * 1024, file_size)
        response = Response(
            generate_chunked_film(video_path, 0, first_chunk_size),
            206,
            mimetype="video/mp4"
        )
        response.headers["Content-Range"] = f"bytes 0-{first_chunk_size - 1}/{file_size}"
        response.headers["Accept-Ranges"] = "bytes"
        response.headers["Content-Length"] = str(first_chunk_size)
        response.headers["Cache-Control"] = "no-cache"
        return response

    # Range qo'llab-quvvatlash
    byte1, byte2 = 0, None
    match = range_header.replace("bytes=", "").split("-")
    
    if match[0]:
        byte1 = int(match[0])
    
    if len(match) > 1 and match[1]:
        byte2 = int(match[1])
    
    length = file_size - byte1
    if byte2 is not None:
        length = byte2 - byte1 + 1
    
    response = Response(
        generate_chunked_film(video_path, byte1, length),
        206,
        mimetype="video/mp4"
    )
    response.headers.add("Content-Range", f"bytes {byte1}-{byte1 + length - 1}/{file_size}")
    response.headers.add("Accept-Ranges", "bytes")
    response.headers.add("Content-Length", str(length))
    response.headers.add("Cache-Control", "no-cache")
    
    return response

# ============ API ============
@app.route('/api/check/<kod>')
def check_film(kod):
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id FROM films WHERE kod = ?", (kod.upper(),))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"exists": True}), 200
    return jsonify({"exists": False}), 404

# ============ FOYDALANUVCHI SAHIFALARI ============
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

# ============ ADMIN PANEL ============
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        parol = request.form.get('parol')
        if parol != ADMIN_PASSWORD:
            return render_template('admin.html', login=False, xato="Parol noto'g'ri!")
        
        db_path = os.path.join(BASE_DIR, 'database.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM films ORDER BY id DESC")
        filmlar = [{'id': r[0], 'kod': r[1], 'nomi': r[2], 'tafsilot': r[3], 'yil': r[4], 'janr': r[5], 'rasm': r[6], 'fayl_nomi': r[7]} for r in c.fetchall()]
        c.execute("SELECT * FROM shorts ORDER BY sana DESC")
        shorts_list = [{'id': r[0], 'sarlavha': r[1], 'tafsilot': r[2], 'fayl_nomi': r[3], 'sana': r[4]} for r in c.fetchall()]
        conn.close()
        return render_template('admin.html', login=True, parol=parol, filmlar=filmlar, shorts_list=shorts_list)
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
        return "Video fayl kerak!", 400
    
    ext = fayl.filename.rsplit('.', 1)[1].lower()
    yangi_nom = f"{kod}.{ext}"
    fayl.save(os.path.join(app.config['UPLOAD_FOLDER_FILMS'], yangi_nom))
    
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
        c.execute("INSERT INTO yangi_filmlar (film_id) VALUES (?)", (film_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER_FILMS'], yangi_nom))
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
    fayl.save(os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], yangi_nom))
    
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO shorts (sarlavha, tafsilot, fayl_nomi) VALUES (?, ?, ?)",
              (sarlavha, tafsilot, yangi_nom))
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
