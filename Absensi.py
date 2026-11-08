import streamlit as st
import pandas as pd
import cv2
import numpy as np
import pyotp
import time
from datetime import datetime
from io import BytesIO
from PIL import Image

# ====================================================
# CONFIGURASI UTAMA KANTOR
# ====================================================
# Menggunakan Secret Key Base32 standar (Simpan rahasia di server)
SECRET_KEY = "SUPERSECRETBASE32KEYABSENSI2026"
totp = pyotp.TOTP(SECRET_KEY, interval=30)  # Kode verifikasi berganti setiap 30 detik

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
st.set_page_config(page_title="Sistem Absensi Stabil", layout="centered")
st.title("🔒 Sistem Absensi QR Dinamis Kantor")

# Pilihan Menu untuk Admin Monitor dan Karyawan
mode = st.sidebar.selectbox("Pilih Mode Aplikasi", ["📱 Menu Absen Karyawan", "📺 Display Monitor Kantor (Token Generator)"])

# ====================================================
# MODE A: MONITOR KANTOR (GENERATOR TOKEN)
# Dipajang di TV / Tablet Kantor depan Resepsionis
# ====================================================
if mode == "📺 Display Monitor Kantor (Token Generator)":
    st.subheader("📺 Layar Utama Monitor Kehadiran Kantor")
    st.caption("Token kode di bawah ini otomatis berubah setiap 30 detik. Karyawan harus melakukan scan secara real-time di lokasi.")
    
    token_placeholder = st.empty()
    time_placeholder = st.empty()
    
    while True:
        current_token = totp.now()
        time_remaining = totp.interval - (time.time() % totp.interval)
        
        with token_placeholder.container():
            st.markdown(f"""
            <div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
                <h1 style='font-size: 60px; color: #1f77b4; letter-spacing: 5px; margin: 0;'>{current_token}</h1>
                <p style='color: #555; margin-top: 10px;'>Masukkan kode TOKEN 6-digit dinamis ini ke HP Anda atau Scan QR</p>
            </div>
            """, unsafe_view_allowed=True)
            
        with time_placeholder.container():
            st.metric(label="Masa Berlaku Kode Kehadiran", value=f"{int(time_remaining)} detik")
            
        time.sleep(1)
        if mode != "📺 Display Monitor Kantor (Token Generator)":
            break

# ====================================================
# MODE B: MENU ABSEN KARYAWAN (AKSES VIA HP INDIVIDU)
# ====================================================
elif mode == "📱 Menu Absen Karyawan":
    st.subheader("Silakan Isi Kehadiran Anda")
    
    emp_id = st.selectbox("Pilih Profil ID Karyawan", list(KARYAWAN_DATA.keys()), format_func=lambda x: f"{x} - {KARYAWAN_DATA[x]}")
    
    st.write("---")
    st.markdown("### Metode Absensi: Masukkan Kode OTP Live Kantor")
    st.caption("Lihat layar monitor TV kantor saat ini, lalu ketikkan 6 digit angka yang tertera di sana.")
    
    # Input Token Dinamis
    token_input = st.text_input("Masukkan 6 Digit Token Kantor Saat Ini", max_chars=6, placeholder="Contoh: 123456")
    
    if st.button("Kirim Kehadiran", use_container_width=True):
        if token_input:
            # Melakukan verifikasi token dengan toleransi 1 interval (antisipasi delay pengetikan karyawan)
            is_valid = totp.verify(token_input, valid_window=1)
            
            if is_valid:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Cek double absen
                sudah_absen = any(d['ID'] == emp_id for d in st.session_state.attendance_db)
                
                if not sudah_absen:
                    st.success(f"🎉 ABSENSI BERHASIL! Selamat bekerja, {KARYAWAN_DATA[emp_id]}.")
                    st.session_state.attendance_db.append({
                        "ID": emp_id,
                        "Nama": KARYAWAN_DATA[emp_id],
                        "Waktu": now_str,
                        "Status": "Hadir Valid"
                    })
                else:
                    st.warning("⚠️ Anda sudah tercatat hadir hari ini.")
            else:
                st.error("❌ Token Kedaluwarsa atau Salah! Sila lihat kode terbaru yang ada di layar monitor kantor.")
        else:
            st.warning("⚠️ Mohon isi 6 digit token kantor terlebih dahulu.")

    # 📊 Ringkasan Laporan
    if st.session_state.attendance_db:
        st.write("---")
        st.subheader("📊 Log Absen Hari Ini")
        df = pd.DataFrame(st.session_state.attendance_db)
        st.dataframe(df, use_container_width=True)
