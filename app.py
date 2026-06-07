import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, Response, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER_FILMS'] = 'static/uploads/films'
app.config['UPLOAD_FOLDER_SHORTS'] = 'static/uploads/shorts'
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024

ALLOWED_VIDEO = {'mp4', 'avi', 'mkv', 'mov', 'webm', 'm4v'}
ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER_FILMS'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_SHORTS'], exist_ok=True)
os.makedirs('static/uploads', exist_ok=True)

ADMIN_PASSWORD = 'admin123'

def init_db():
    conn = sqlite3.connect('database.db')
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
    print("✅ DB yaratildi!")

init_db()

def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

# ============ TEZ SHORTS STREAMING (OPTIMALLASHTIRILGAN) ============
@app.route('/stream-shorts/<int:id>')
def stream_shorts(id):
    """Ultra tez shorts streaming - 128KB chunks"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT fayl_nomi FROM shorts WHERE id = ?", (id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return "Short topilmadi!", 404
    
    video_path = os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], row[0])
    
    if not os.path.exists(video_path):
        return "Video topilmadi!", 404
    
    def generate_fast():
        with open(video_path, 'rb') as f:
            while True:
                chunk = f.read(128 * 1024)  # 128KB - juda tez
                if not chunk:
                    break
                yield chunk
    
    response = Response(generate_fast(), 200, mimetype='video/mp4')
    response.headers.add('Cache-Control', 'public, max-age=31536000')
    response.headers.add('Content-Type', 'video/mp4')
    return response

# ============ TEZ FILM STREAMING ============
@app.route('/stream/<kod>')
def stream_video(kod):
    conn = sqlite3.connect('database.db')
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
    
    def generate_chunks(video_path, start, end, chunk_size=512*1024):
        with open(video_path, 'rb') as f:
            f.seek(start)
            bytes_remaining = end - start + 1
            while bytes_remaining > 0:
                chunk = f.read(min(chunk_size, bytes_remaining))
                if not chunk:
                    break
                bytes_remaining -= len(chunk)
                yield chunk
    
    if range_header:
        byte_range = range_header.replace('bytes=', '').split('-')
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        response = Response(generate_chunks(video_path, start, end), 206, mimetype='video/mp4')
        response.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
        response.headers.add('Accept-Ranges', 'bytes')
        response.headers.add('Content-Length', str(end - start + 1))
    else:
        first_chunk = min(2 * 1024 * 1024, file_size)
        response = Response(generate_chunks(video_path, 0, first_chunk), 206, mimetype='video/mp4')
        response.headers.add('Content-Range', f'bytes 0-{first_chunk}/{file_size}')
        response.headers.add('Accept-Ranges', 'bytes')
        response.headers.add('Content-Length', str(first_chunk))
    
    response.headers.add('Cache-Control', 'no-cache')
    return response

# ============ API ============
@app.route('/api/check/<kod>')
def check_film(kod):
    conn = sqlite3.connect('database.db')
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
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM shorts ORDER BY sana DESC")
    rows = c.fetchall()
    shorts = [{'id': r[0], 'sarlavha': r[1], 'tafsilot': r[2], 'fayl_nomi': r[3], 'sana': r[4]} for r in rows]
    conn.close()
    return render_template('index.html', shorts=shorts)

@app.route('/film/<kod>')
def film(kod):
    conn = sqlite3.connect('database.db')
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
        conn = sqlite3.connect('database.db')
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
        return render_template('admin.html', login=True, parol=parol, filmlar=filmlar, shorts_list=shorts_list, total_films=total_films, total_shorts=total_shorts)
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
        return f"Video fayl kerak! Ruxsat: {', '.join(ALLOWED_VIDEO)}", 400
    ext = fayl.filename.rsplit('.', 1)[1].lower()
    yangi_nom = f"{kod}.{ext}"
    fayl.save(os.path.join(app.config['UPLOAD_FOLDER_FILMS'], yangi_nom))
    rasm_nomi = None
    if 'rasm' in request.files:
        rasm = request.files['rasm']
        if rasm and rasm.filename and allowed_file(rasm.filename, ALLOWED_IMAGE):
            rasm_ext = rasm.filename.rsplit('.', 1)[1].lower()
            rasm_nomi = f"{kod}.{rasm_ext}"
            rasm.save(os.path.join('static/uploads', rasm_nomi))
    conn = sqlite3.connect('database.db')
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
        return f"Video fayl kerak! Ruxsat: {', '.join(ALLOWED_VIDEO)}", 400
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = fayl.filename.rsplit('.', 1)[1].lower()
    yangi_nom = f"short_{timestamp}.{ext}"
    fayl.save(os.path.join(app.config['UPLOAD_FOLDER_SHORTS'], yangi_nom))
    conn = sqlite3.connect('database.db')
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
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT fayl_nomi, rasm FROM films WHERE id = ?", (id,))
    row = c.fetchone()
    if row:
        fayl_nomi, rasm = row
        fayl_path = os.path.join(app.config['UPLOAD_FOLDER_FILMS'], fayl_nomi)
        if os.path.exists(fayl_path):
            os.remove(fayl_path)
        if rasm:
            rasm_path = os.path.join('static/uploads', rasm)
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
    conn = sqlite3.connect('database.db')
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

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('static/uploads', filename)

@app.errorhandler(404)
def not_found(error):
    return "<h1>404 - Sahifa topilmadi!</h1><a href='/'>Bosh sahifaga qaytish</a>", 404

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                    🎬 KINOTOP - ULTRA TEZ VERSIYA 🎬                     ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║  🌐 LOCAL: http://localhost:5000                                        ║
    ║  🔐 ADMIN: http://localhost:5000/admin                                  ║
    ║  📝 PAROL: admin123                                                      ║
    ║                                                                          ║
    ║  ⚡ XUSUSIYATLAR:                                                        ║
    ║     ✓ Faqat ko'rinayotgan short o'ynaydi                                ║
    ║     ✓ Barcha shortslar oldindan yuklanadi                               ║
    ║     ✓ Ovoz aralashmaydi (faqat bitta video)                             ║
    ║     ✓ 128KB chunk - juda tez yuklash                                    ║
    ║     ✓ Video tugaganda keyingisiga o'tish                                ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', debug=True, port=5000, threaded=True)