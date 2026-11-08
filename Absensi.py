import streamlit as st
import pandas as pd
import cv2
import numpy as np
import os
import piexif
from datetime import datetime
from io import BytesIO
from PIL import Image

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

FILE_DATABASE = "absen_master.csv"

# Inisialisasi awal file CSV agar database selalu siap di server
if not os.path.exists(FILE_DATABASE):
    df_kosong = pd.DataFrame(columns=["Tanggal", "ID", "Nama", "Waktu Presensi", "Koordinat GPS", "Latitude", "Longitude", "Status"])
    df_kosong.to_csv(FILE_DATABASE, index=False)

def muat_data_absen():
    if os.path.exists(FILE_DATABASE):
        try:
            df = pd.read_csv(FILE_DATABASE)
            df['Koordinat GPS'] = df['Koordinat GPS'].astype(str)
            return df
        except:
            return pd.DataFrame(columns=["Tanggal", "ID", "Nama", "Waktu Presensi", "Koordinat GPS", "Latitude", "Longitude", "Status"])
    return pd.DataFrame(columns=["Tanggal", "ID", "Nama", "Waktu Presensi", "Koordinat GPS", "Latitude", "Longitude", "Status"])

# Inisialisasi memori tampilan session state agar data sinkron dengan database server
if "data_log_view" not in st.session_state:
    st.session_state["data_log_view"] = muat_data_absen()

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
    df_baru.to_csv(FILE_DATABASE, mode='a', header=False, index=False)
    st.session_state["data_log_view"] = pd.concat([st.session_state["data_log_view"], df_baru], ignore_index=True)

# Fungsi untuk mengonversi data derajat EXIF GPS iPhone ke format desimal numerik standar
def konversi_ke_derajat_desimal(nilai, referensi):
    try:
        derajat = float(nilai[0][0]) / float(nilai[0][1])
        menit = float(nilai[1][0]) / float(nilai[1][1])
        detik = float(nilai[2][0]) / float(nilai[2][1])
        
        desimal = derajat + (menit / 60.0) + (detik / 3600.0)
        if referensi in ['S', 'W']:
            desimal = -desimal
        return desimal
    except:
        return None

# Fungsi utama mengekstrak metadata GPS tersembunyi dari foto iPhone karyawan
def ekstrak_gps_dari_foto(bytes_gambar):
    try:
        exif_dict = piexif.load(bytes_gambar)
        gps_data = exif_dict.get("GPS")
        
        if gps_data:
            lat_val = gps_data.get(piexif.GPSIFD.GPSLatitude)
            lat_ref = gps_data.get(piexif.GPSIFD.GPSLatitudeRef).decode('utf-8')
            lon_val = gps_data.get(piexif.GPSIFD.GPSLongitude)
            lon_ref = gps_data.get(piexif.GPSIFD.GPSLongitudeRef).decode('utf-8')
            
            if lat_val and lon_val:
                lat = konversi_ke_derajat_desimal(lat_val, lat_ref)
                lon = konversi_ke_derajat_desimal(lon_val, lon_ref)
                if lat and lon:
                    return lat, lon, f"{lat:.6f},{lon:.6f}"
        return None, None, "GPS Foto Tidak Aktif"
    except:
        return None, None, "Gagal Membaca EXIF"

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Master Absensi')
    processed_data = output.getvalue()
    return processed_data

# ====================================================
# INTERFACE APLIKASI
# ====================================================
st.set_page_config(page_title="Absensi Metadata GPS", layout="centered")
st.title("🔒 Sistem Absensi QR Code & Koordinat Permanen")
st.caption("Aplikasi mengekstrak tanda tangan koordinat GPS langsung dari metadata file foto asli HP karyawan.")

# Pilihan Karyawan
emp_id = st.selectbox("Pilih Profil ID Karyawan", list(KARYAWAN_DATA.keys()), format_func=lambda x: f"{x} - {KARYAWAN_DATA[x]}")

st.write("---")
st.subheader("📸 Pindai QR Code Kantor")
st.info("💡 **Tips iPhone:** Pastikan fitur lokasi kamera aktif di iPhone Anda (*Settings > Privacy > Location Services > Camera > Precise Location*).")

picture = st.file_uploader("Ketuk di sini untuk membuka Kamera iPhone & Ambil Foto QR", type=["png", "jpg", "jpeg"])

if picture is not None:
    bytes_data = picture.read()
    
    # PROSES EKSTRAKSI KOORDINAT DARI METADATA FOTO IPHONE (Pasti Berhasil)
    user_lat, user_lon, koordinat_karyawan = ekstrak_gps_dari_foto(bytes_data)
    
    cv_img = Image.open(BytesIO(bytes_data))
    open_cv_image = np.array(cv_img)
    
    if len(open_cv_image.shape) == 3 and open_cv_image.shape[2] == 4:
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGBA2RGB)
    elif len(open_cv_image.shape) == 2:
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_GRAY2RGB)
        
    open_cv_image = open_cv_image[:, :, ::-1].copy()
    
    st.image(bytes_data, caption="Pratinjau Foto QR Anda", width=200)
    
    with st.spinner("Memproses data presensi..."):
        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(open_cv_image)
        
        if data:
            if data == KODE_QR_SAH:
                waktu_sekarang = datetime.now()
                hari_ini = waktu_sekarang.strftime("%Y-%m-%d")
                waktu_str = waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S")
                
                df_lama = st.session_state["data_log_view"]
                sudah_absen = False
                if not df_lama.empty:
                    sudah_absen = ((df_lama['ID'] == emp_id) & (df_lama['Tanggal'] == hari_ini)).any()
                
                if not sudah_absen:
                    simpan_absen_baru(hari_ini, emp_id, KARYAWAN_DATA[emp_id], waktu_str, koordinat_karyawan, user_lat, user_lon, "Hadir Sah")
                    st.success(f"🎉 PRESENSI BERHASIL DICATAT! Selamat bertugas, {KARYAWAN_DATA[emp_id]}.")
                    if koordinat_karyawan != "GPS Foto Tidak Aktif":
                        st.info(f"📍 Koordinat HP Anda terekam: `{koordinat_karyawan}`")
                else:
                    st.warning(f"⚠️ Profil ID {emp_id} sudah terdaftar hadir pada hari ini ({hari_ini}).")
            else:
                st.error("❌ Autentikasi Gagal! Kode QR yang Anda potret salah atau tidak sah.")
        else:
            st.error("📷 Pembacaan kode gagal. Pastikan foto berjarak dekat, sejajar lurus, dan tidak buram.")

# ====================================================
# 📊 PRESENTASI TABEL DATA LOG ABSENSI LIVE MURNI
# ====================================================
st.write("---")
st.subheader("📊 Master Riwayat & Lokasi Scan Karyawan")

df_master = st.session_state["data_log_view"]
st.dataframe(df_master.sort_values(by="Waktu Presensi", ascending=False), use_container_width=True)

# Tampilkan peta visual jika ada koordinat numerik desimal yang valid dari foto
df_peta = df_master.dropna(subset=['Latitude', 'Longitude'])
if not df_peta.empty:
    st.write("### 🗺️ Peta Visualisasi Lokasi Scan Karyawan")
    df_map_engine = df_peta[['Latitude', 'Longitude']].rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})
    st.map(df_map_engine, zoom=11)

# MODUL UNDUH MASTER BERKAS
st.write("### 📥 Unduh Master Berkas Log Absensi")
col1, col2 = st.columns(2)

with col1:
    excel_data = to_excel(df_master) if not df_master.empty else b""
    st.download_button(
        label="🟢 Unduh Dokumen Excel (.xlsx)",
        data=excel_data,
        file_name=f"master_absen_koordinat_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=df_master.empty,
        use_container_width=True
    )
    
with col2:
    csv_data = df_master.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="🔵 Unduh Dokumen CSV (.csv)",
        data=csv_data,
        file_name=f"master_absen_koordinat_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        disabled=df_master.empty,
        use_container_width=True
    )
