import streamlit as st
import pandas as pd
import cv2
import numpy as np
import os
from datetime import datetime
from io import BytesIO
from PIL import Image
from streamlit_js_eval import streamlit_js_eval

# ====================================================
# CONFIGURASI UTAMA KANTOR
# ====================================================
KODE_QR_SAH = "KANTOR_UTAMA_SECRET_KEY_2026" 

KARYAWAN_DATA = {
    "EMP001": "Eka Sulawestara",
    "EMP002": "Diny Herlita",
    "EMP003": "Eureka Annisa Naira",
    "EMP004": "Eustacia Redinka Amayra"
}

# Nama file database master di server hosting
FILE_DATABASE = "absen_master.csv"

# Fungsi membaca database CSV
def muat_data_absen():
    if os.path.exists(FILE_DATABASE):
        try:
            return pd.read_csv(FILE_DATABASE)
        except:
            return pd.DataFrame(columns=["Tanggal", "ID", "Nama", "Waktu Presensi", "Koordinat GPS", "Status"])
    else:
        return pd.DataFrame(columns=["Tanggal", "ID", "Nama", "Waktu Presensi", "Koordinat GPS", "Status"])

# Fungsi menulis data log baru termasuk titik koordinat GPS karyawan
def simpan_absen_baru(tanggal, emp_id, nama, waktu_str, koordinat, status):
    df_baru = pd.DataFrame([{
        "Tanggal": tanggal,
        "ID": emp_id,
        "Nama": nama,
        "Waktu Presensi": waktu_str,
        "Koordinat GPS": koordinat,
        "Status": status
    }])
    if not os.path.exists(FILE_DATABASE):
        df_baru.to_csv(FILE_DATABASE, index=False)
    else:
        df_baru.to_csv(FILE_DATABASE, mode='a', header=False, index=False)

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Master Absensi')
    processed_data = output.getvalue()
    return processed_data

# ====================================================
# INTERFACE APLIKASI
# ====================================================
st.set_page_config(page_title="Absensi Tracking QR", layout="centered")
st.title("🔒 Sistem Absensi QR Code & Geolokasi")
st.caption("Pilih nama Anda, rekam lokasi GPS Anda saat ini, lalu ambil foto QR Code kantor.")

# Dropdown Karyawan
emp_id = st.selectbox("Pilih Profil ID Karyawan", list(KARYAWAN_DATA.keys()), format_func=lambda x: f"{x} - {KARYAWAN_DATA[x]}")

st.write("---")
st.subheader("📍 Langkah 1: Ambil Titik Koordinat GPS Anda")
st.caption("Khusus pengguna iPhone/Android, Anda wajib mengeklik tombol di bawah ini agar browser dapat mengunci posisi koordinat Anda saat upload.")

# Tombol manual pemicu sinkronisasi GPS agar lolos dari aturan pemblokiran Safari iframe
if st.button("🛰️ Ambil / Dapatkan Lokasi GPS Saya Saat Ini", use_container_width=True):
    st.session_state["pemicu_gps"] = True

# Injeksi JavaScript untuk membaca koordinat dengan akurasi tinggi
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
loc_string = streamlit_js_eval(data_string=js_gps_script, key=f"gps_iphone_{st.session_state.get('pemicu_gps', False)}")

koordinat_karyawan = "Belum Terdeteksi"

if loc_string:
    if "ERROR" not in loc_string:
        koordinat_karyawan = loc_string
        st.success(f"✅ Koordinat Anda Terkunci: `{koordinat_karyawan}`")
    else:
        st.error("❌ Browser memblokir akses lokasi. Sila aktifkan izin GPS browser Anda.")
else:
    st.warning("⚠️ Status GPS belum masuk. Silakan ketuk tombol hitam **'🛰️ Ambil / Dapatkan Lokasi GPS Saya'** di atas dan pilih 'Allow/Izinkan'.")

st.write("---")
st.subheader("📸 Langkah 2: Pindai QR Code Kantor")

picture = st.file_uploader("Ketuk di sini untuk membuka Kamera iPhone & Foto QR", type=["png", "jpg", "jpeg"])

if picture is not None:
    bytes_data = picture.read()
    cv_img = Image.open(BytesIO(bytes_data))
    open_cv_image = np.array(cv_img)
    
    if len(open_cv_image.shape) == 3 and open_cv_image.shape == 4:
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGBA2RGB)
    elif len(open_cv_image.shape) == 2:
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_GRAY2RGB)
        
    open_cv_image = open_cv_image[:, :, ::-1].copy()
    
    st.image(bytes_data, caption="Pratinjau Foto QR Anda", width=200)
    
    with st.spinner("Memvalidasi QR Code..."):
        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(open_cv_image)
        
        if data:
            if data == KODE_QR_SAH:
                waktu_sekarang = datetime.now()
                hari_ini = waktu_sekarang.strftime("%Y-%m-%d")
                waktu_str = waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S")
                
                df_lama = muat_data_absen()
                sudah_absen = False
                if not df_lama.empty:
                    sudah_absen = ((df_lama['ID'] == emp_id) & (df_lama['Tanggal'] == hari_ini)).any()
                
                if not sudah_absen:
                    # Simpan data absensi termasuk teks string koordinat asli dari HP karyawan
                    simpan_absen_baru(hari_ini, emp_id, KARYAWAN_DATA[emp_id], waktu_str, koordinat_karyawan, "Hadir Sah (QR Verified)")
                    st.success(f"🎉 ABSENSI BERHASIL! Selamat bekerja, {KARYAWAN_DATA[emp_id]}.")
                else:
                    st.warning(f"⚠️ {KARYAWAN_DATA[emp_id]} sudah terdaftar hadir pada hari ini ({hari_ini}).")
            else:
                st.error("❌ QR Code Salah! Ini bukan QR Code resmi kantor.")
        else:
            st.error("📷 QR Code tidak terdeteksi. Dekatkan kamera dan pastikan fokus.")

# ----------------------------------------------------
# 📊 PANEL LOG DATA MASTER MULTI-HARI & UNDUH BERKAS
# ----------------------------------------------------
df_master = muat_data_absen()

if not df_master.empty:
    st.write("---")
    st.subheader("📊 Master Riwayat & Lokasi Upload Karyawan")
    st.caption("Kolom 'Koordinat GPS' merekam titik asli posisi HP karyawan saat melakukan upload berkas.")
    
    # Menampilkan tabel absensi permanen multi-hari
    st.dataframe(df_master.sort_values(by="Waktu Presensi", ascending=False), use_container_width=True)
    
    st.write("### 📥 Unduh Seluruh Log Data Karyawan")
    col1, col2 = st.columns(2)
    
    with col1:
        excel_data = to_excel(df_master)
        st.download_button(
            label="🟢 Unduh Rekap Excel (.xlsx)",
            data=excel_data,
            file_name=f"rekap_absen_koordinat_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    with col2:
        csv_data = df_master.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="🔵 Unduh Rekap CSV (.csv)",
            data=csv_data,
            file_name=f"rekap_absen_koordinat_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
