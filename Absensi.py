import streamlit as st
import qrcode
import time
import hashlib
from io import BytesIO
from datetime import datetime

# Simulasi database sederhana (Gunakan Database asli seperti SQLite/PostgreSQL untuk production)
if 'attendance_db' not in st.session_state:
    st.session_state['attendance_db'] = []

# Konfigurasi Token Rahasia agar tidak bisa ditebak manual
SECRET_SALT = "SuperSecretSalt123!" 

def generate_secure_token(interval_seconds=15):
    """Membuat token unik yang berubah setiap interval detik tertentu"""
    current_time = time.time()
    # Membagi waktu saat ini dengan interval (misal 15 detik) untuk menghasilkan angka konstan dalam jendela waktu itu
    time_window = int(current_time / interval_seconds)
    
    # Hash gabungan time window dan salt rahasia
    raw_token = f"{time_window}_{SECRET_SALT}"
    secure_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    return secure_hash, time_window

# --- NAVIGASI ANTARMUKA ---
st.sidebar.title("Menu Absensi QR")
page = st.sidebar.radio("Pilih Tampilan:", ["Monitor QR (Admin)", "Scan Absen (Pengguna/HP)"])

# ==========================================
# HALAMAN 1: MONITOR QR (DITAMPILKAN DI KANTOR/KELAS)
# ==========================================
if page == "Monitor QR (Admin)":
    st.title("📺 Layar Absensi QR Dinamis")
    st.write("QR Code di bawah ini akan kedaluwarsa dan berubah secara otomatis dalam **15 detik**.")

    # Membuat container kosong agar bisa di-refresh terus-menerus
    placeholder = st.empty()

    # Loop untuk simulasi refresh otomatis (Streamlit run berkala)
    while True:
        token, window_id = generate_secure_token(interval_seconds=15)
        
        # Payload yang dimasukkan ke dalam QR Code
        qr_data = f"ABSEN_{window_id}_{token}"
        
        # Generate gambar QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Konversi ke format Bytes agar bisa dibaca Streamlit st.image
        buf = BytesIO()
        img.save(buf, format="PNG")
        byte_im = buf.getvalue()
        
        # Tampilkan di Streamlit
        with placeholder.container():
            st.image(byte_im, caption=f"Scan Sekarang! Terakhir diupdate pada: {datetime.now().strftime('%H:%M:%S')}", width=300)
            st.progress((int(time.time()) % 15) / 15.0, text="Menunggu pergantian kode QR...")
            
        time.sleep(1) # Cek & update bar progres setiap 1 detik

# ==========================================
# HALAMAN 2: SCAN ABSEN (BUKA DI HP MASING-MASING)
# ==========================================
elif page == "Scan Absen (Pengguna/HP)":
    st.title("📱 Pindai QR Kehadiran")
    
    nama_user = st.text_input("Masukkan Nama / ID Anda:", placeholder="Contoh: Budi Santoso")
    
    st.info("Gunakan kamera bawaan Streamlit di bawah ini untuk memindai QR Code dinamis yang ada di layar monitor.")
    
    # Menggunakan kamera bawaan Streamlit
    img_file = st.camera_input("Arahkan Kamera ke QR Code")
    
    if img_file and nama_user:
        import cv2
        import numpy as np
        
        # Membaca gambar dari kamera
        file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
        opencv_img = cv2.imdecode(file_bytes, 1)
        
        # Deteksi dan Decode QR Code menggunakan OpenCV
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(opencv_img)
        
        if data and data.startswith("ABSEN_"):
            try:
                # Memecah data QR: ["ABSEN", "window_id", "token"]
                _, qr_window_id, qr_token = data.split("_")
                
                # Memvalidasi token saat ini dengan token pada QR yang dipindai
                _, current_window_id = generate_secure_token(interval_seconds=15)
                
                # Toleransi 1 jendela waktu ke belakang (jika telat beberapa detik karena loading kamera)
                is_valid = False
                for w in [current_window_id, current_window_id - 1]:
                    check_raw = f"{w}_{SECRET_SALT}"
                    expected_hash = hashlib.sha256(check_raw.encode()).hexdigest()
                    if expected_hash == qr_token:
                        is_valid = True
                        break
                
                if is_valid:
                    # Cek apakah user sudah absen hari ini/sesi ini (opsional)
                    log_sukses = f"Hadir: {nama_user} pada pukul {datetime.now().strftime('%H:%M:%S')}"
                    
                    if log_sukses not in st.session_state['attendance_db']:
                        st.session_state['attendance_db'].append(log_sukses)
                        st.success(f"🎉 Absensi BERHASIL diverifikasi! Selamat datang, {nama_user}.")
                    else:
                        st.warning("⚠️ Anda sudah melakukan absensi untuk sesi ini.")
                else:
                    st.error("❌ Gagal! QR Code sudah Kedaluwarsa (Expired). Silakan scan ulang kode terbaru di layar monitor.")
            except Exception as e:
                st.error("❌ QR Code tidak valid atau format salah.")
        else:
            st.error("🔍 QR Code tidak terdeteksi. Pastikan gambar QR Code jelas dan tidak buram.")
            
    # Menampilkan Rekap Absensi Sementara
    st.write("---")
    st.subheader("📋 Log Kehadiran Hari Ini (Real-time)")
    if st.session_state['attendance_db']:
        for log in st.session_state['attendance_db']:
            st.text(log)
    else:
        st.caption("Belum ada data kehadiran saat ini.")
