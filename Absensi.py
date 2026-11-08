import streamlit as st
import pandas as pd
import cv2
import numpy as np
from datetime import datetime
from io import BytesIO
from PIL import Image

# ====================================================
# CONFIGURASI UTAMA KANTOR
# ====================================================
# Teks rahasia yang tertanam di dalam QR Code Statis Kantor Anda
KODE_QR_SAH = "KANTOR_UTAMA_SECRET_KEY_2026" 

KARYAWAN_DATA = {
    "EMP001": "Eka Sulawestara",
    "EMP002": "Diny Herlita",
    "EMP003": "Eureka Annisa Naira",
    "EMP004": "Eustacia Redinka Amayra"
}

if "attendance_db" not in st.session_state:
    st.session_state.attendance_db = []

# ====================================================
# INTERFACE APLIKASI
# ====================================================
st.set_page_config(page_title="Absensi QR Statis", layout="centered")
st.title("🔒 Sistem Absensi QR Code Kantor")
st.caption("Silakan pilih nama Anda dan ambil foto QR Code resmi kantor yang telah disediakan.")

# Dropdown Karyawan
emp_id = st.selectbox("Pilih Profil ID Karyawan", list(KARYAWAN_DATA.keys()), format_func=lambda x: f"{x} - {KARYAWAN_DATA[x]}")

st.write("---")
st.markdown("### 📸 Pindai QR Code Kantor")

# Menggunakan file uploader untuk memicu kamera native iPhone secara langsung tanpa blokir privasi Apple
picture = st.file_uploader("Ketuk di sini untuk membuka Kamera iPhone & Foto QR", type=["png", "jpg", "jpeg"])

if picture is not None:
    # Baca berkas gambar hasil jepretan kamera
    bytes_data = picture.read()
    cv_img = Image.open(BytesIO(bytes_data))
    open_cv_image = np.array(cv_img)
    
    # Normalisasi konversi warna RGBA ke standar RGB jika terdeteksi dari iPhone
    if len(open_cv_image.shape) == 3 and open_cv_image.shape[2] == 4:
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGBA2RGB)
    elif len(open_cv_image.shape) == 2:
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_GRAY2RGB)
        
    open_cv_image = open_cv_image[:, :, ::-1].copy() # Convert RGB ke BGR OpenCV
    
    # Menampilkan miniatur pratinjau hasil foto di layar web
    st.image(bytes_data, caption="Pratinjau Foto QR Anda", width=200)
    
    with st.spinner("Mengekstrak data QR Code..."):
        # Inisialisasi mesin OpenCV QR Detector
        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(open_cv_image)
        
        if data:
            # Validasi apakah teks QR Code sama dengan kunci sah kantor
            if data == KODE_QR_SAH:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Cek pencegahan double absen untuk orang yang sama hari ini
                sudah_absen = any(d['ID'] == emp_id for d in st.session_state.attendance_db)
                
                if not sudah_absen:
                    st.success(f"🎉 ABSENSI BERHASIL! Selamat bekerja, {KARYAWAN_DATA[emp_id]}.")
                    st.session_state.attendance_db.append({
                        "ID": emp_id,
                        "Nama": KARYAWAN_DATA[emp_id],
                        "Waktu Presensi": now_str,
                        "Status": "Hadir Sah (QR Verified)"
                    })
                else:
                    st.warning("⚠️ Anda sudah terdaftar hadir hari ini.")
            else:
                st.error("❌ QR Code Salah! Ini bukan QR Code resmi yang diterbitkan oleh kantor.")
        else:
            st.error("📷 QR Code tidak terdeteksi. Pastikan Anda memotret kertas QR secara dekat, fokus, lurus, dan tidak blur.")

# 📊 Panel Log Hasil Absensi Hari Ini
if st.session_state.attendance_db:
    st.write("---")
    st.subheader("📊 Laporan Absensi Hari Ini")
    df = pd.DataFrame(st.session_state.attendance_db)
    st.dataframe(df, use_container_width=True)
