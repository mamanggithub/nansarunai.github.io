"""
Fungsi-fungsi bantuan untuk Koperasi Token Emas
"""

import random
import string
from datetime import datetime
import secrets
import re

# ====================================================
# FUNGSI GENERATE KODE UNIK
# ====================================================

def generate_nomor_anggota():
    """
    Membuat nomor anggota unik
    Format: KTA-YYYY-XXXXX
    Contoh: KTA-2026-12345
    """
    tahun = datetime.now().year
    random_num = ''.join(random.choices(string.digits, k=5))
    return f"KTA-{tahun}-{random_num}"

def generate_user_id():
    """
    Membuat user ID unik untuk QR code
    Format: user_XXXXXXXX
    """
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"user_{random_str}"

def generate_token_code():
    """
    Generate kode token unik: EMAS-YYYYMMDD-HHMMSS-XXXXXX
    """
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"EMAS-{date_str}-{time_str}-{random_part}"

def generate_transaction_id():
    """
    Generate ID transaksi: TRX-YYYYMMDD-XXXXX
    """
    date_str = datetime.now().strftime("%Y%m%d")
    random_num = ''.join(random.choices(string.digits + string.ascii_uppercase, k=5))
    return f"TRX-{date_str}-{random_num}"

# ====================================================
# QR CODE
# ====================================================

def generate_qr_code_data(user_id, nama):
    """
    Generate data untuk QR code
    Format: KOPERASI:user_id:nama
    """
    return f"KOPERASI:{user_id}:{nama}"

def parse_qr_code_data(qr_data):
    """
    Parse data dari QR code
    Return: (user_id, nama) atau None jika invalid
    """
    try:
        parts = qr_data.split(':')
        if len(parts) == 3 and parts[0] == "KOPERASI":
            return int(parts[1]), parts[2]
    except:
        pass
    return None, None

# ====================================================
# FUNGSI HITUNG ADMIN & TOKEN
# ====================================================

def hitung_nilai_token_dari_emas(harga_emas_per_gram):
    """
    Hitung nilai 1 token berdasarkan harga emas
    Rumus: harga_emas_per_gram / 2000
    """
    return harga_emas_per_gram / 2000

def hitung_biaya_admin_rupiah(nilai_rupiah, persen=0.02):
    """
    Hitung biaya admin 2% dalam rupiah
    """
    return nilai_rupiah * persen

def hitung_jumlah_token_dari_rupiah(rupiah, harga_emas_per_gram):
    """
    Hitung berapa token yang bisa dibeli dengan rupiah (untuk jual beli)
    """
    nilai_per_token = hitung_nilai_token_dari_emas(harga_emas_per_gram)
    return int(rupiah / nilai_per_token)

# ====================================================
# FUNGSI HITUNG TUNGGAKAN
# ====================================================

def hitung_bulan_tunggakan(terakhir_bayar):
    """
    Menghitung berapa bulan tunggakan iuran wajib
    """
    if not terakhir_bayar:
        return 0
    
    sekarang = datetime.now()
    # Hitung selisih bulan
    selisih_bulan = (sekarang.year - terakhir_bayar.year) * 12 + \
                    (sekarang.month - terakhir_bayar.month)
    
    return max(0, selisih_bulan)

# ====================================================
# FUNGSI VALIDASI
# ====================================================

def validasi_email(email):
    """
    Validasi format email
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validasi_username(username):
    """
    Validasi username (hanya huruf, angka, underscore)
    """
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return re.match(pattern, username) is not None

# ====================================================
# FUNGSI FORMAT ANGKA
# ====================================================

def format_rupiah(angka):
    """
    Format angka ke format rupiah
    Contoh: 1000000 -> Rp 1.000.000
    """
    try:
        return f"Rp {angka:,.0f}".replace(',', '.')
    except:
        return "Rp 0"

def format_token(jumlah):
    """
    Format jumlah token
    """
    try:
        return f"{jumlah:,} token".replace(',', '.')
    except:
        return "0 token"

def format_gram(gram):
    """
    Format gram emas
    """
    try:
        return f"{gram:.4f} gram"
    except:
        return "0 gram"

# ====================================================
# FUNGSI KEAMANAN
# ====================================================

def generate_api_key():
    """
    Generate API key untuk admin
    """
    return secrets.token_urlsafe(32)

def hash_password(password):
    """
    Hash password (placeholder - nanti pakai passlib)
    """
    # Sementara return asli, nanti ganti dengan hashing beneran
    return password

def verify_password(password, hashed):
    """
    Verifikasi password (placeholder)
    """
    return password == hashed

# ====================================================
# TESTING FUNGSI
# ====================================================
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING FUNGSI HELPERS")
    print("=" * 50)
    
    print(f"Nomor anggota: {generate_nomor_anggota()}")
    print(f"User ID: {generate_user_id()}")
    print(f"Token code: {generate_token_code()}")
    print(f"Transaction ID: {generate_transaction_id()}")
    print(f"QR Data: {generate_qr_code_data(123, 'Warung Budi')}")
    
    user_id, nama = parse_qr_code_data("KOPERASI:123:Warung Budi")
    print(f"Parse QR: user_id={user_id}, nama={nama}")
    
    print(f"\nHitung nilai token dari emas Rp 1.200.000/gram: Rp {hitung_nilai_token_dari_emas(1200000):.2f}")
    print(f"Biaya admin Rp 50.000: Rp {hitung_biaya_admin_rupiah(50000):.2f}")
    
    print(f"\nFormat Rp 1000000: {format_rupiah(1000000)}")
    print(f"Format token 1500: {format_token(1500)}")
    print(f"Format gram 0.1234: {format_gram(0.1234)}")
    
    # Test validasi
    print(f"\nValidasi email 'user@example.com': {validasi_email('user@example.com')}")
    print(f"Validasi email 'user@example': {validasi_email('user@example')}")
    print(f"Validasi username 'user123': {validasi_username('user123')}")
    print(f"Validasi username 'us': {validasi_username('us')}")