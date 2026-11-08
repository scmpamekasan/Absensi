import streamlit as st
import pandas as pd
import cv2
import numpy as np
import os
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

# Tentukan nama file database fisik di server
FILE_DATABASE = "absen_master.csv"

# Fungsi untuk membaca data dari file CSV fisik
def muat_data_absen():
    if os.path.exists(FILE_DATABASE):
        try:
            return pd.read_csv(FILE_DATABASE)
        except:
            return pd.DataFrame(columns=["Tanggal", "ID", "Nama", "Waktu Presensi", "Status"])
    else:
        return pd.DataFrame(columns=["Tanggal", "ID", "Nama", "Waktu Presensi", "Status"])

# Fungsi untuk menyimpan baris data baru ke file CSV fisik
def simpan_absen_baru(tanggal, emp_id, nama, waktu_str, status):
    df_baru = pd.DataFrame([{
        "Tanggal": tanggal,
        "ID": emp_id,
        "Nama": nama,
        "Waktu Presensi": waktu_str,
        "Status": status
    }])
    
    if not os.path.exists(FILE_DATABASE):
        df_baru.to_csv(FILE_DATABASE, index=False)
    else:
        df_baru.to_csv(FILE_DATABASE, mode='a', header=False, index=False)

# Fungsi pembantu konversi berkas unduhan Excel
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Master Absensi')
    processed_data = output.getvalue()
    return processed_data

# ====================================================
# INTERFACE APLIKASI
# ====================================================
st.set_page_config(page_title="Absensi QR Permanen", layout="centered")
st.set_page_config(page_title="Absensi QR Proteksi", layout="centered")
st.title("🔒 Sistem Absensi QR Code Kantor")
st.caption("Data absensi tersimpan permanen di server dan dapat diunduh kapan saja oleh admin.")
st.caption("Sistem dilengkapi modul deteksi otomatis berkas manipulasi galeri non-live.")

# Dropdown Karyawan
emp_id = st.selectbox("Pilih Profil ID Karyawan", list(KARYAWAN_DATA.keys()), format_func=lambda x: f"{x} - {KARYAWAN_DATA[x]}")

st.write("---")
st.markdown("### 📸 Pindai QR Code Kantor")
st.warning("⚠️ WAJIB Pilih Opsi 'Take Photo' (Kamera Langsung). Memilih dari Galeri/Photo Library akan membuat absen Anda DITOLAK.")

picture = st.file_uploader("Ketuk di sini untuk membuka Kamera iPhone & Foto QR", type=["png", "jpg", "jpeg"])

if picture is not None:
    bytes_data = picture.read()
    cv_img = Image.open(BytesIO(bytes_data))
    open_cv_image = np.array(cv_img)
    # 🛡️ PROTEKSI VALIDASI JALUR AMBIL FOTO (ANTI-GALERI)
    nama_berkas = picture.name.lower()

    if len(open_cv_image.shape) == 3 and open_cv_image.shape[2] == 4:
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGBA2RGB)
    elif len(open_cv_image.shape) == 2:
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_GRAY2RGB)
    # Deteksi kecocokan nama file default jepretan live kamera seluler iOS/Android
    is_live_camera = "image" in nama_berkas or "photo" in nama_berkas or nama_berkas.startswith("captured")

    if not is_live_camera:
        st.error(f"❌ ABSENSI DITOLAK! Terdeteksi kecurangan. Anda mengunggah file dari Galeri/Photo Library ({picture.name}). Anda wajib menggunakan menu 'Take Photo' untuk mengambil foto secara langsung di tempat.")
    else:
        bytes_data = picture.read()
        cv_img = Image.open(BytesIO(bytes_data))
        open_cv_image = np.array(cv_img)

    open_cv_image = open_cv_image[:, :, ::-1].copy()
    
    st.image(bytes_data, caption="Pratinjau Foto QR Anda", width=200)
    
    with st.spinner("Mengekstrak data QR Code..."):
        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(open_cv_image)
        if len(open_cv_image.shape) == 3 and open_cv_image.shape[2] == 4:
            open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGBA2RGB)
        elif len(open_cv_image.shape) == 2:
            open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_GRAY2RGB)
            
        open_cv_image = open_cv_image[:, :, ::-1].copy()

        if data:
            if data == KODE_QR_SAH:
                # Ambil objek waktu saat ini secara presisi
                waktu_sekarang = datetime.now()
                hari_ini = waktu_sekarang.strftime("%Y-%m-%d")
                waktu_str = waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S")
                
                # Muat database fisik untuk pengecekan data
                df_lama = muat_data_absen()
                
                # Validasi proteksi ganda: Hanya tolak jika ID sudah absen di TANGGAL yang sama
                sudah_absen = False
                if not df_lama.empty:
                    sudah_absen = ((df_lama['ID'] == emp_id) & (df_lama['Tanggal'] == hari_ini)).any()
                
                if not sudah_absen:
                    # Simpan langsung ke file CSV fisik di server
                    simpan_absen_baru(hari_ini, emp_id, KARYAWAN_DATA[emp_id], waktu_str, "Hadir Sah (QR Verified)")
                    st.success(f"🎉 ABSENSI BERHASIL! Selamat bekerja, {KARYAWAN_DATA[emp_id]}.")
        st.image(bytes_data, caption="Pratinjau Foto QR Anda", width=200)
        
        with st.spinner("Mengekstrak data QR Code..."):
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
                        simpan_absen_baru(hari_ini, emp_id, KARYAWAN_DATA[emp_id], waktu_str, "Hadir Sah (Kamera Live)")
                        st.success(f"🎉 ABSENSI BERHASIL! Selamat bekerja, {KARYAWAN_DATA[emp_id]}.")
                    else:
                        st.warning(f"⚠️ {KARYAWAN_DATA[emp_id]} sudah terdaftar hadir pada hari ini ({hari_ini}).")
                else:
                    st.warning(f"⚠️ {KARYAWAN_DATA[emp_id]} sudah terdaftar hadir pada hari ini ({hari_ini}).")
                    st.error("❌ QR Code Salah! Ini bukan QR Code resmi kantor.")
            else:
                st.error("❌ QR Code Salah! Ini bukan QR Code resmi kantor.")
        else:
            st.error("📷 QR Code tidak terdeteksi. Dekatkan kamera dan pastikan fokus.")
                st.error("📷 QR Code tidak terdeteksi. Dekatkan kamera dan pastikan fokus.")

# ----------------------------------------------------
# 📊 PANEL LOG DATA MULTI-HARI & DOWNLOAD BERKAS
# 📊 PANEL LOG RIWAYAT
# ----------------------------------------------------
df_master = muat_data_absen()

if not df_master.empty:
    st.write("---")
    st.subheader("📊 Master Riwayat Absensi Karyawan")
    
    # Menampilkan seluruh riwayat gabungan hari ini dan hari-hari sebelumnya
    st.dataframe(df_master.sort_values(by="Waktu Presensi", ascending=False), use_container_width=True)

    st.write("### 📥 Unduh Seluruh Log Data Karyawan")
    col1, col2 = st.columns(2)
    
    with col1:
        excel_data = to_excel(df_master)
        st.download_button(
            label="🟢 Unduh Rekap Excel (.xlsx)",
            data=excel_data,
            file_name=f"rekap_absen_master_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    with col2:
        csv_data = df_master.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="🔵 Unduh Rekap CSV (.csv)",
            data=csv_data,
            file_name=f"rekap_absen_master_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
