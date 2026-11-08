import streamlit as st
import pandas as pd
import cv2
import numpy as np
from datetime import datetime
from io import BytesIO
from PIL import Image
from math import radians, cos, sin, asin, sqrt
from streamlit_geolocation import streamlit_geolocation

# ====================================================
# CONFIGURASI KANTOR
# ====================================================
KANTOR_LAT = -7.310502   # Latitude Rungkut Surabaya
KANTOR_LON = 112.798985  # Longitude Rungkut Surabaya
RADIUS_MAKSIMAL = 100.0  # Jarak radius dalam meter

KODE_QR_SAH = "KANTOR_UTAMA_SECRET_KEY_2026" 

KARYAWAN_DATA = {
    "EMP001": "Eka Sulawestara",
    "EMP002": "Diny Herlita",
    "EMP003": "Eureka Annisa Naira",
    "EMP004": "Eustacia Redinka Amayra"
}

def hitung_jarak(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000 
    return c * r

if "attendance_db" not in st.session_state:
    st.session_state.attendance_db = []

# ====================================================
# INTERFACE APLIKASI
# ====================================================
st.set_page_config(page_title="Sistem Absensi iPhone Fix", layout="centered")
st.title("🔒 Sistem Absensi QR + GPS Kantor")

# ----------------------------------------------------
# MODUL 1: AMBIL LOKASI GPS (MENGGUNAKAN TOMBOL RESMI IOS COMPATIBLE)
# ----------------------------------------------------
st.subheader("📍 Langkah 1: Klik Tombol di Bawah untuk Kirim GPS")
st.caption("Khusus iPhone, Anda wajib mengetuk tombol di bawah ini untuk mengaktifkan izin GPS Safari.")

# Komponen tombol khusus geolokasi resmi
location = streamlit_geolocation()

user_lat, user_lon = None, None
lokasi_valid = False
jarak_ke_kantor = None

# Memeriksa apakah pengguna sudah menekan tombol dan koordinat didapatkan
if location and location['latitude'] is not None:
    try:
        user_lat = float(location['latitude'])
        user_lon = float(location['longitude'])
        jarak_ke_kantor = hitung_jarak(user_lat, user_lon, KANTOR_LAT, KANTOR_LON)
        
        st.info(f"🔍 GPS Anda: Lat {user_lat:.6f}, Lon {user_lon:.6f}")
        st.info(f"📏 Jarak Anda ke Kantor: **{jarak_ke_kantor:.1f} meter**")
        
        if jarak_ke_kantor <= RADIUS_MAKSIMAL:
            st.success("✅ Lokasi Terverifikasi! Anda berada di dalam area kantor.")
            lokasi_valid = True
        else:
            st.error(f"❌ Posisi Anda di luar radius kantor! (Batas maks: {RADIUS_MAKSIMAL}m).")
            lokasi_valid = False
    except Exception as e:
        st.error(f"Gagal memproses koordinat: {e}")
else:
    st.warning("⚠️ Sinyal GPS belum masuk. Klik tombol hitam di atas dan pilih 'Allow/Izinkan Lokasi'.")

# ----------------------------------------------------
# MODUL 2: PEMINDAIAN QR DENGAN TOMBOL NATIVE UPLOADER
# ----------------------------------------------------
st.write("---")
st.subheader("📸 Langkah 2: Pindai QR Code Kantor")

emp_id = st.selectbox("Pilih Profil ID Anda", list(KARYAWAN_DATA.keys()), format_func=lambda x: f"{x} - {KARYAWAN_DATA[x]}")

# Tombol kamera sengaja dilepas dari if-lokasi agar Anda bisa tes kameranya dulu
picture = st.file_uploader("Klik di sini untuk membuka Kamera iPhone Anda", type=["png", "jpg", "jpeg"])

if picture is not None:
    if lokasi_valid:
        bytes_data = picture.read()
        cv_img = Image.open(BytesIO(bytes_data))
        open_cv_image = np.array(cv_img)
        
        if len(open_cv_image.shape) == 3 and open_cv_image.shape[2] == 4:
            open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGBA2RGB)
            
        open_cv_image = open_cv_image[:, :, ::-1].copy()
        
        # Ekstraksi kode QR
        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(open_cv_image)
        
        if data:
            if data == KODE_QR_SAH:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sudah_absen = any(d['ID'] == emp_id for d in st.session_state.attendance_db)
                
                if not sudah_absen:
                    st.success(f"🎉 ABSEN BERHASIL! Selamat bekerja, {KARYAWAN_DATA[emp_id]}.")
                    st.session_state.attendance_db.append({
                        "ID": emp_id,
                        "Nama": KARYAWAN_DATA[emp_id],
                        "Waktu": now_str,
                        "Jarak": f"{jarak_ke_kantor:.1f}m",
                        "Status": "Hadir Sah"
                    })
                else:
                    st.warning("⚠️ Anda sudah melakukan absen hari ini.")
            else:
                st.error("❌ QR Code Palsu! Ini bukan kode resmi dari papan pengumuman kantor.")
        else:
            st.error("📷 Gambar kurang jelas. Pastikan memotret QR Code secara tegak lurus, fokus, dan dekat.")
    else:
        st.error("🔒 Maaf, Absen ditolak! Lokasi GPS Anda belum valid atau di luar radius kantor.")

# ----------------------------------------------------
# MODUL 3: TABEL DATA KEHADIRAN
# ----------------------------------------------------
if st.session_state.attendance_db:
    st.write("---")
    st.subheader("📊 Log Absen Hari Ini")
    df = pd.DataFrame(st.session_state.attendance_db)
    st.dataframe(df, use_container_width=True)
