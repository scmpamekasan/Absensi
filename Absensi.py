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

# Berkas penyimpanan database lokal fisik di server cloud
FILE_DATABASE = "absen_master.csv"

# Fungsi membaca data terakumulasi dari file CSV server
def muat_data_absen():
    if os.path.exists(FILE_DATABASE):
        try:
            df = pd.read_csv(FILE_DATABASE)
            # Pastikan kolom Koordinat GPS bertipe string agar tidak terjadi error parsing
            df['Koordinat GPS'] = df['Koordinat GPS'].astype(str)
            return df
        except:
            return pd.DataFrame(columns=["Tanggal", "ID", "Nama", "Waktu Presensi", "Koordinat GPS", "Latitude", "Longitude", "Status"])
    else:
        return pd.DataFrame(columns=["Tanggal", "ID", "Nama", "Waktu Presensi", "Koordinat GPS", "Latitude", "Longitude", "Status"])

# Fungsi menulis baris log baru ke file CSV server secara permanen
def simpan_absen_baru(tanggal, emp_id, nama, waktu_str, koordinat_str, lat, lon, status):
    df_baru = pd.DataFrame([{
        "Tanggal": tanggal,
        "ID": emp_id,
        "Nama": nama,
        "Waktu Presensi": waktu_str,
        "Koordinat GPS": koordinat_str,
        "Latitude": lat,
        "Longitude": lon,
        "Status": status
    }])
    if not os.path.exists(FILE_DATABASE):
        df_baru.to_csv(FILE_DATABASE, index=False)
    else:
        df_baru.to_csv(FILE_DATABASE, mode='a', header=False, index=False)

# Konversi DataFrame ke format Excel buffer
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Master Absensi')
    processed_data = output.getvalue()
    return processed_data

# ====================================================
# INTERFACE APLIKASI
# ====================================================
st.set_page_config(page_title="Absensi QR Permanent Log", layout="centered")
st.title("🔒 Sistem Absensi QR Code & Koordinat Permanen")
st.caption("Data log presensi tersimpan permanen di server fisik bersama rekaman titik koordinat GPS HP karyawan.")

# Dropdown Pemilihan Identitas Karyawan
emp_id = st.selectbox("Pilih Profil ID Karyawan", list(KARYAWAN_DATA.keys()), format_func=lambda x: f"{x} - {KARYAWAN_DATA[x]}")

st.write("---")
st.subheader("📍 Langkah 1: Kunci Lokasi Koordinat Anda")
st.caption("Wajib ketuk tombol di bawah ini sebelum mengunggah foto QR Code agar koordinat presensi Anda terekam valid.")

# Tombol pemicu interaksi sensor lokasi seluler browser
if st.button("🛰️ Ambil / Sinkronisasikan Koordinat GPS HP", use_container_width=True):
    st.session_state["pemicu_gps_sinkron"] = True

# Skrip injeksi API Geolocation HTML5 High Accuracy
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
loc_string = streamlit_js_eval(data_string=js_gps_script, key=f"gps_permanen_{st.session_state.get('pemicu_gps_sinkron', False)}")

koordinat_karyawan = "Belum Terdeteksi"
current_lat, current_lon = None, None

if loc_string:
    if "ERROR" not in loc_string:
        try:
            koordinat_karyawan = loc_string
            current_lat, current_lon = map(float, loc_string.split(','))
            st.success(f"✅ Titik Koordinat Berhasil Terkunci: `{koordinat_karyawan}`")
        except:
            st.warning("⏳ Memproses string koordinat numerik...")
    else:
        st.error("❌ Akses lokasi ditolak browser. Sila aktifkan Location Services di pengaturan browser Anda.")
else:
    st.warning("⚠️ Menunggu data sinyal GPS. Sila ketuk tombol hitam **'🛰️ Ambil / Sinkronisasikan Koordinat GPS HP'** di atas.")

st.write("---")
st.subheader("📸 Langkah 2: Unggah Jepretan QR Code Kantor")

picture = st.file_uploader("Ketuk di sini untuk mengambil foto QR Code Kantor", type=["png", "jpg", "jpeg"])

if picture is not None:
    bytes_data = picture.read()
    cv_img = Image.open(BytesIO(bytes_data))
    open_cv_image = np.array(cv_img)
    
    if len(open_cv_image.shape) == 3 and open_cv_image.shape[2] == 4:
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGBA2RGB)
    elif len(open_cv_image.shape) == 2:
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_GRAY2RGB)
        
    open_cv_image = open_cv_image[:, :, ::-1].copy()
    
    st.image(bytes_data, caption="Pratinjau Unggahan Foto QR", width=200)
    
    with st.spinner("Memvalidasi kode matriks QR..."):
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
                    # Tulis log baru ke file CSV server secara permanen termasuk lintang dan bujur
                    simpan_absen_baru(hari_ini, emp_id, KARYAWAN_DATA[emp_id], waktu_str, koordinat_karyawan, current_lat, current_lon, "Hadir Sah")
                    st.success(f"🎉 PRESENSI BERHASIL DICATAT! Selamat bertugas, {KARYAWAN_DATA[emp_id]}.")
                else:
                    st.warning(f"⚠️ Profil ID {emp_id} sudah terdaftar hadir pada hari ini ({hari_ini}).")
            else:
                st.error("❌ Autentikasi Gagal! Kode QR yang Anda potret salah atau tidak sah.")
        else:
            st.error("📷 Pembacaan kode gagal. Pastikan foto berjarak dekat, sejajar lurus, dan tidak buram.")

# ----------------------------------------------------
# 📊 PRESENTASI TABEL DATA LOG ABSENSI PERMANEN
# ----------------------------------------------------
df_master = muat_data_absen()

# Bagian ini dijamin akan selalu muncul di layar selama file database absen_master.csv ada di server
if not df_master.empty:
    st.write("---")
    st.subheader("📊 Master Ringkasan Riwayat Log Absensi")
    st.caption("Data di bawah mencakup riwayat kumulatif harian yang tersimpan secara permanen di basis data server.")
    
    # Menampilkan tabel rekap permanen multi-hari diurutkan dari waktu terbaru
    st.dataframe(df_master.sort_values(by="Waktu Presensi", ascending=False), use_container_width=True)
    
    # FILTER DATA VALID UNTUK KEBUTUHAN PEMETAAN GEOGRAFIS
    # Menghapus baris kosong/tanpa GPS agar widget peta tidak memicu error visual
    df_peta = df_master.dropna(subset=['Latitude', 'Longitude'])
    
    if not df_peta.empty:
        st.write("### 🗺️ Peta Visualisasi Lokasi Scan Karyawan")
        # Rename kolom ke format baku Streamlit map engine
        df_map_engine = df_peta[['Latitude', 'Longitude']].rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})
        st.map(df_map_engine, zoom=11)
    
    # MODUL UNDUH DOKUMEN REKAP GABUNGAN OPERASIONAL KANTOR
    st.write("### 📥 Unduh Master Berkas Log Absensi")
    col1, col2 = st.columns(2)
    
    with col1:
        excel_data = to_excel(df_master)
        st.download_button(
            label="🟢 Unduh Dokumen Excel (.xlsx)",
            data=excel_data,
            file_name=f"master_absen_koordinat_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    with col2:
        csv_data = df_master.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="🔵 Unduh Dokumen CSV (.csv)",
            data=csv_data,
            file_name=f"master_absen_koordinat_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
