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
KANTOR_LAT = -7.310502   # Latitude kantor Anda (Surabaya)
KANTOR_LON = 112.798985  # Longitude kantor Anda (Surabaya)
RADIUS_MAKSIMAL = 1000.0  # LONGGAR KAN KE 100 METER untuk antisipasi lonjakan akurasi GPS HP

# Isi QR Code unik kantor Anda yang harus dicetak/dipajang
KODE_QR_SAH = "KANTOR_UTAMA_SECRET_KEY_2026" 

# Data karyawan terdaftar
KARYAWAN_DATA = {
    "EMP001": "Eka Sulawestara",
    "EMP002": "Diny Herlita",
    "EMP003": "Eureka Annisa Naira",
    "EMP004": "Eustacia Redinka Amayra"
}

# Fungsi untuk menghitung jarak antara 2 koordinat GPS (Haversine Formula)
def hitung_jarak(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000 # Radius bumi dalam meter
    return c * r

# Inisialisasi database tiruan di memori
if "attendance_db" not in st.session_state:
    st.session_state.attendance_db = []

# ====================================================
# INTERFACE APLIKASI
# ====================================================
st.set_page_config(page_title="QR & GPS Attendance", layout="centered")
st.title("📱 Absensi HP Karyawan (QR + GPS)")
st.caption("Aplikasi ini mendeteksi lokasi Anda untuk memastikan Anda melakukan scan di area kantor.")

# 1. AMBIL LOKASI GPS KARYAWAN SECARA REAL-TIME (DENGAN HIGH ACCURACY ENABLED)
st.subheader("1. Deteksi Lokasi Anda")

# Menggunakan Opsi enableHighAccuracy agar browser HP dipaksa memakai GPS Hardware, bukan tebakan IP internet
js_gps_script = """
window.navigator.geolocation.getCurrentPosition(
    function(pos) { 
        return pos.coords.latitude + ',' + pos.coords.longitude; 
    }, 
    function(err) { 
        return 'ERROR:' + err.message; 
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
);
"""
loc_string = streamlit_js_eval(data_string=js_gps_script, key="get_location_accurate")

user_lat, user_lon = None, None
lokasi_valid = False
jarak_ke_kantor = 999999.0

if loc_string:
    if "ERROR" in loc_string:
        st.error(f"❌ Browser gagal mengakses GPS: {loc_string}. Pastikan izin lokasi aktif.")
    else:
        try:
            user_lat, user_lon = map(float, loc_string.split(','))
            jarak_ke_kantor = hitung_jarak(user_lat, user_lon, KANTOR_LAT, KANTOR_LON)
            
            # FITUR DEBUG INDIKATOR (Sangat penting agar tahu posisi Anda yang sebenarnya)
            st.info(f"🔍 [INFO GPS HP] Terdeteksi di: Lat {user_lat:.6f}, Lon {user_lon:.6f}")
            st.info(f"📏 [INFO JARAK] Posisi Anda berjarak **{jarak_ke_kantor:.1f} meter** dari titik tengah kantor.")
            
            if jarak_ke_kantor <= RADIUS_MAKSIMAL:
                st.success(f"📍 Lokasi Terverifikasi! Anda berada di area kantor.")
                lokasi_valid = True
            else:
                st.error(f"❌ Jarak Anda ({jarak_ke_kantor:.1f}m) melewati batas toleransi maksimal kantor ({RADIUS_MAKSIMAL}m).")
                lokasi_valid = False
        except Exception as e:
            st.warning(f"⚠️ Gagal memproses data lokasi: {e}")
            lokasi_valid = False
else:
    st.warning("⏳ Menunggu browser mengunci sinyal GPS Anda... Mohon klik 'Allow/Izinkan Lokasi' jika muncul pop-up di layar HP Anda.")
    # Tombol paksa refresh jika browser macet mengambil koordinat awal
    if st.button("🔄 Segarkan Sinyal GPS"):
        st.rerun()

# 2. PROSES SCAN QR CODE (HANYA AKTIF JIKA LOKASI VALID)
st.write("---")
st.subheader("2. Scan QR Code Kantor")

# Pilihan Karyawan
emp_id = st.selectbox("Pilih ID Karyawan Anda", list(KARYAWAN_DATA.keys()), format_func=lambda x: f"{x} - {KARYAWAN_DATA[x]}")

if lokasi_valid:
    picture = st.camera_input("Arahkan kamera HP ke QR Code yang dipajang di kantor")
    
    if picture:
        bytes_data = picture.getvalue()
        cv_img = Image.open(BytesIO(bytes_data))
        open_cv_image = np.array(cv_img)
        open_cv_image = open_cv_image[:, :, ::-1].copy()
        
        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(open_cv_image)
        
        if data:
            if data == KODE_QR_SAH:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Cek pencegahan double absen token
                sudah_absen = any(d['ID'] == emp_id for d in st.session_state.attendance_db)
                
                if not sudah_absen:
                    st.success(f"🎉 ABSEN BERHASIL! Selamat bekerja, {KARYAWAN_DATA[emp_id]}.")
                    st.session_state.attendance_db.append({
                        "ID": emp_id,
                        "Nama": KARYAWAN_DATA[emp_id],
                        "Waktu": now_str,
                        "Jarak (Meter)": f"{jarak_ke_kantor:.1f}m",
                        "Status": "Hadir Verified"
                    })
                else:
                    st.warning("⚠️ Anda sudah terdaftar hadir hari ini.")
            else:
                st.error("❌ QR Code Salah! Ini bukan QR Code resmi kantor.")
        else:
            st.error("📷 QR Code tidak terbaca dengan jelas. Coba dekatkan kamera ke QR Code.")
else:
    st.info(f"🔒 Tombol kamera terkunci. Anda harus masuk ke dalam radius kantor (< {RADIUS_MAKSIMAL} meter).")

# 3. TAMPILKAN HASIL ABSENSI
if st.session_state.attendance_db:
    st.write("---")
    st.subheader("📊 Log Absen Hari Ini")
    df = pd.DataFrame(st.session_state.attendance_db)
    st.dataframe(df, use_container_width=True)
