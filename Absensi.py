import streamlit as st
import pandas as pd
import cv2
import numpy as np
from datetime import datetime
from io import BytesIO
from PIL import Image
from math import radians, cos, sin, asin, sqrt
from streamlit_js_eval import streamlit_js_eval

# ====================================================
# CONFIGURASI KANTOR (UBAH SESUAI KANTOR ANDA)
# ====================================================
KANTOR_LAT = -7.310502   # Koordinat Latitude Kantor Pusat (Surabaya)
KANTOR_LON = 112.798985  # Koordinat Longitude Kantor Pusat (Surabaya)
RADIUS_MAKSIMAL = 100.0  # Batas radius toleransi spasial operasional (Meter)

# Kunci string rahasia terenkripsi pada fisik lembar cetak dokumen QR Code
KODE_QR_SAH = "KANTOR_UTAMA_SECRET_KEY_2026" 

# Basis data profil identitas penamaan entitas internal karyawan resmi
KARYAWAN_DATA = {
    "EMP001": "Eka Sulawestara",
    "EMP002": "Diny Herlita",
    "EMP003": "Eureka Annisa Naira",
    "EMP004": "Eustacia Redinka Amayra"
}

# Perhitungan komputasi jarak menggunakan metode matematis Haversine Formula
def hitung_jarak(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000  # Radius konstanta matematis keliling bumi dalam satuan meter
    return c * r

# Inisialisasi struktur penyimpanan tabel persisten lokal memori internal runtime
if "attendance_db" not in st.session_state:
    st.session_state.attendance_db = []

# ====================================================
# STRUKTUR ANTARMUKA APLIKASI UTAMA (USER INTERFACE)
# ====================================================
st.set_page_config(page_title="QR & GPS Attendance System", layout="centered")
st.title("🔒 Sistem Absensi Seluler Karyawan (QR + GPS)")
st.caption("Aplikasi pencatatan absensi real-time berbasis verifikasi geolokasi perangkat keras dan pemindaian optik.")

# ----------------------------------------------------
# MODUL 1: EVALUASI LOKASI GEOSPASIAL PERANGKAT
# ----------------------------------------------------
st.subheader("📍 1. Validasi Posisi Geolokasi Anda")

# Injeksi runtime JavaScript API Geolocation dengan parameter High Accuracy Hardware
js_gps_script = """
window.navigator.geolocation.getCurrentPosition(
    function(pos) { 
        return pos.coords.latitude + ',' + pos.coords.longitude; 
    }, 
    function(err) { 
        return 'ERROR:' + err.message; 
    },
    { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
);
"""
loc_string = streamlit_js_eval(data_string=js_gps_script, key="get_location_accurate_ios_fix")

user_lat, user_lon = None, None
lokasi_valid = False
jarak_ke_kantor = 999999.0

if loc_string:
    if "ERROR" in loc_string:
        st.error(f"❌ Akses sensor geolokasi ditolak oleh browser: {loc_string}. Sila buka setelan privasi.")
    else:
        try:
            user_lat, user_lon = map(float, loc_string.split(','))
            jarak_ke_kantor = hitung_jarak(user_lat, user_lon, KANTOR_LAT, KANTOR_LON)
            
            # Panel Visual Output Indikator Data Diagnostik Spasial HP
            st.info(f"🔍 Koordinat Terbaca: Lat {user_lat:.6f}, Lon {user_lon:.6f}")
            st.info(f"📏 Jarak Estimasi: **{jarak_ke_kantor:.1f} meter** dari pusat titik koordinat kantor.")
            
            if jarak_ke_kantor <= RADIUS_MAKSIMAL:
                st.success("✅ Lokasi Terverifikasi! Anda berada di dalam batas jangkauan area kerja kantor.")
                lokasi_valid = True
            else:
                st.error(f"❌ Verifikasi Gagal! Anda berada di luar radius toleransi instansi (Maksimal {RADIUS_MAKSIMAL}m).")
                lokasi_valid = False
        except Exception as e:
            st.warning(f"⚠️ Kegagalan struktural interpretasi string koordinat: {e}")
            lokasi_valid = False
else:
    st.warning("⏳ Menghubungkan ke satelit GPS... Harap klik opsi 'Allow/Izinkan Lokasi' jika muncul jendela dialog pada layar smartphone Anda.")
    if st.button("🔄 Segarkan Sinyal Geolokasi (GPS)"):
        st.rerun()

# ----------------------------------------------------
# MODUL 2: INTEGRASI PEMINDAIAN OPTIK QR CODE
# ----------------------------------------------------
st.write("---")
st.subheader("📷 2. Pemindaian Kode Matriks QR")

# Komponen dropdown seleksi pemetaan entitas data register
emp_id = st.selectbox("Pilih Profil ID Karyawan", list(KARYAWAN_DATA.keys()), format_func=lambda x: f"{x} - {KARYAWAN_DATA[x]}")

if lokasi_valid:
    # Menggunakan modul unggah berkas yang kompatibel secara menyeluruh untuk memicu sistem kamera native seluler
    picture = st.file_uploader("Buka Modul Kamera HP / Pilih Foto Dokumen QR Kantor", type=["png", "jpg", "jpeg"])
    
    if picture is not None:
        # Konversi struktur input streams data ke bentuk matriks piksel gambar numerik
        bytes_data = picture.read()
        cv_img = Image.open(BytesIO(bytes_data))
        open_cv_image = np.array(cv_img)
        
        # Penanganan normalisasi dimensi ruang matriks warna gambar tipe RGBA ke format standard RGB
        if len(open_cv_image.shape) == 3 and open_cv_image.shape[2] == 4:
            open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGBA2RGB)
        elif len(open_cv_image.shape) == 2:
            open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_GRAY2RGB)
            
        open_cv_image = open_cv_image[:, :, ::-1].copy()  # Transformasi format urutan ruang warna dari RGB ke BGR OpenCV
        
        # Penayangan miniatur visualisasi citra gambar hasil pemotretan kamera HP
        st.image(bytes_data, caption="Dokumen gambar yang akan dievaluasi", width=240)
        
        # Proses inisialisasi modul detektor ekstradiksi dekode data visual QR Code
        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(open_cv_image)
        
        if data:
            if data == KODE_QR_SAH:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Prosedur pencegahan manipulasi pengiriman entri ganda (Double Entry Kehadiran)
                sudah_absen = any(d['ID'] == emp_id for d in st.session_state.attendance_db)
                
                if not sudah_absen:
                    st.success(f"🎉 PROSES ABSENSI BERHASIL! Selamat bertugas kembali, {KARYAWAN_DATA[emp_id]}.")
                    st.session_state.attendance_db.append({
                        "ID": emp_id,
                        "Nama": KARYAWAN_DATA[emp_id],
                        "Waktu Registrasi": now_str,
                        "Deviasi Spasial": f"{jarak_ke_kantor:.1f}m",
                        "Status Validasi": "Hadir Sah (Verified)"
                    })
                else:
                    st.warning("⚠️ Entitas data identitas Anda sudah tercatat melakukan absensi kehadiran pada hari ini.")
            else:
                st.error("❌ Token Dokumen Salah! Kode matriks QR yang Anda pindai tidak terdaftar di server kantor resmi.")
        else:
            st.error("📷 Gagal mengekstrak kode. Pastikan citra gambar diambil secara dekat, tegak lurus, terfokus, dan dengan pencahayaan memadai.")
else:
    st.info(f"🔒 Gerbang modul pemindaian tertutup otomatis hingga koordinat GPS terverifikasi berada di dalam radius < {RADIUS_MAKSIMAL} meter.")

# ----------------------------------------------------
# MODUL 3: MONITOR DATA OUTPUT LOG ABSENSI
# ----------------------------------------------------
if st.session_state.attendance_db:
    st.write("---")
    st.subheader("📊 Laporan Ringkasan Kehadiran Hari Ini")
    df = pd.DataFrame(st.session_state.attendance_db)
    st.dataframe(df, use_container_width=True)
