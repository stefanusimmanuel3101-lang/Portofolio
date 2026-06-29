import os
import pymysql
from flask import Flask,render_template,request,redirect,url_for,session
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import resend 

# 1. Inisialisasi
load_dotenv()
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    resend_api_key=os.getenv('RESEND_API_KEY'),
    secure=True
)
app = Flask(__name__)
app.config['Immanuel31'] = os.getenv('Immanuel31')
app.secret_key = os.getenv('FLASK_SECRET_KEY')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

# 2. Fungsi Koneksi Database
def get_db_connection():
    # Parsing URI atau gunakan variabel terpisah
    # Pastikan SSL diatur jika TiDB mengharuskan (bisa disesuaikan)
    conn = pymysql.connect(
        host=os.getenv('DB_HOST', 'gateway01.ap-southeast-1.prod.aws.tidbcloud.com'),
        user=os.getenv('DB_USER', 'utwGT8aaL4von19.root'),
        password=os.getenv('DB_PASSWORD', '4m1Y8scgKCuwb7bm'),
        database=os.getenv('DB_NAME', 'portofolio'),
        port=4000
    )
    return conn

# 3. Routes / Logika Aplikasi
@app.route('/')
def index():
    try:
        conn = get_db_connection()
        # WAJIB gunakan DictCursor agar data yang ditarik berbentuk kamus (dictionary)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 1. Eksekusi penarikan data Profil
        cursor.execute("SELECT * FROM profil LIMIT 1")
        data_profil = cursor.fetchone()
        
        # Jaring pengaman (Fail-safe): Jika tabel profil kosong, sistem tidak akan crash
        if not data_profil:
            data_profil = {
                'nama': 'Admin', 
                'profesi': 'Sistem Informasi', 
                'bio': 'Data profil belum diinput ke database.'
            }

        # 2. Eksekusi penarikan data Proyek (Asumsi kode lama lo)
        cursor.execute("SELECT * FROM proyek")
        data_proyek = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # PENTING: Oper kedua data tersebut ke HTML
        return render_template('index.html', profil=data_profil, proyeks=data_proyek)
        
    except Exception as e:
        return f"Kesalahan Sistem: {e}"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password_input = request.form.get('password')
        
        # Validasi: Apakah password yang diketik sama dengan di .env?
        if password_input == ADMIN_PASSWORD:
            session['admin_logged_in'] = True  # Berikan kartu akses
            return redirect(url_for('index'))
        else:
            return "Password Salah! Silakan kembali dan coba lagi."
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Hapus kartu akses dari browser
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))
    
@app.route('/profil/edit', methods=['GET', 'POST'])
def edit_profil():
    # Pasang dua baris ini di baris pertama dalam fungsi edit & tambah
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    # Jika sekadar membuka halaman (GET), tampilkan formulir
    if request.method == 'GET':
        return render_template('edit.html')
    
    # Jika tombol simpan ditekan (POST), proses datanya
    if request.method == 'POST':
        # 1. Tangkap teks dari formulir
        nama_baru = request.form.get('nama')
        profesi_baru = request.form.get('profesi')
        bio_baru = request.form.get('bio')
        
        # 2. Tangkap file gambar
        foto = request.files.get('foto')
        foto_url = None
        
        # 3. Jika ada foto yang diunggah, kirim ke Cloudinary
        if foto and foto.filename != '':
            # Proses ke Cloudinary
            upload_result = cloudinary.uploader.upload(foto)
            # Tarik URL aman yang dihasilkan Cloudinary
            foto_url = upload_result.get('secure_url')
        
        # 4. Simpan semuanya ke TiDB
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if foto_url:
            # Update semua termasuk URL foto baru
            cursor.execute('''
                UPDATE profil 
                SET nama=%s, profesi=%s, bio=%s, foto_url=%s
            ''', (nama_baru, profesi_baru, bio_baru, foto_url))
        else:
            # Update teks saja, biarkan foto lama tetap ada
            cursor.execute('''
                UPDATE profil 
                SET nama=%s, profesi=%s, bio=%s
            ''', (nama_baru, profesi_baru, bio_baru))
            
        conn.commit()
        cursor.close()
        conn.close()
        
        # Kembalikan ke halaman utama untuk melihat hasilnya
        return redirect(url_for('index'))
    
@app.route('/proyek/tambah', methods=['GET', 'POST'])
def tambah_proyek():
    # Pasang dua baris ini di baris pertama dalam fungsi edit & tambah
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    if request.method == 'GET':
        return render_template('add_proyek.html')
        
    if request.method == 'POST':
        judul = request.form.get('judul')
        deskripsi = request.form.get('deskripsi')
        link = request.form.get('link')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        # Memasukkan data proyek baru ke database
        cursor.execute('INSERT INTO proyek (judul, deskripsi, link) VALUES (%s, %s, %s)', (judul, deskripsi, link))
        conn.commit()
        cursor.close()
        conn.close()
        
        return redirect(url_for('index'))
@app.route('/proyek/hapus/<int:id>', methods=['POST'])
def hapus_proyek(id):

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Eksekusi Pemusnahan Data
        cursor.execute("DELETE FROM proyek WHERE id = %s", (id,))
        conn.commit() # Nyawa dari eksekusi database
        
        cursor.close()
        conn.close()
        
        return redirect(url_for('index'))
    except Exception as e:
        return f"Kegagalan sistem saat menghapus: {e}"
    
@app.route('/kirim-pesan', methods=['POST'])
def kirim_pesan():
    nama = request.form.get('nama')
    email_pengirim = request.form.get('email')
    pesan = request.form.get('pesan')
    
    try:
        # Eksekusi API Resend
        resend.Emails.send({
            "from": "onboarding@resend.dev", # Resend mewajibkan email pengirim default mereka untuk tier gratis
            "to": "email.asli.lo@gmail.com", # Email tujuan lo
            "subject": f"Pesan Portofolio dari {nama}",
            "html": f"<p><strong>Pengirim:</strong> {nama} ({email_pengirim})</p><p>{pesan}</p>"
        })
        return "Pesan berhasil dikirim ke satelit Resend. Silakan cek inbox lo."
    except Exception as e:
        return f"Gagal mengirim pesan: {e}"
    
# 4. Eksekusi
if __name__ == '__main__':
    app.run(debug=True, port=5000)