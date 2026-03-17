"""
File konfigurasi untuk Koperasi Token Emas
Semua pengaturan penting ada di sini
"""

import os

# ====================================================
# KONVERSI DASAR
# ====================================================
TOKEN_PER_GRAM = 2000  # 1 gram emas = 2000 token
GRAM_PER_TOKEN = 1 / TOKEN_PER_GRAM  # 0.0005 gram per token

# ====================================================
# IURAN ANGGOTA
# ====================================================
IURAN_AWAL = 12000  # Deposit iuran untuk 1 tahun
IURAN_BULANAN = 1000  # Dipotong otomatis tiap bulan

# ====================================================
# BIAYA ADMIN (2%)
# ====================================================
BIAYA_ADMIN_PERSEN = 0.02  # 2%

# ====================================================
# MODAL AWAL KOPERASI
# ====================================================
MODAL_EMAS_AWAL_GRAM = 1  # 1 gram emas sebagai modal awal
STOK_TOKEN_AWAL = MODAL_EMAS_AWAL_GRAM * TOKEN_PER_GRAM  # 2000 token

# ====================================================
# DATABASE
# ====================================================
# Database URL (bisa diganti dengan environment variable)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/koperasi.db")

# Untuk PostgreSQL di production:
# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/koperasi")

# ====================================================
# SERVER & API
# ====================================================
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# Secret key untuk JWT (nanti untuk login)
SECRET_KEY = os.getenv("SECRET_KEY", "ganti-dengan-secret-key-aman-di-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# ====================================================
# CORS (Cross-Origin Resource Sharing)
# ====================================================
# Origin yang diizinkan (untuk website & android)
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080",
    "file://",
    "*",  # Untuk development
]

# ====================================================
# CACHE & PERFORMANCE
# ====================================================
CACHE_DURATION_HARGA_EMAS = 300  # 5 menit
CACHE_DURATION_STATIC = 3600  # 1 jam

# ====================================================
# BLOCKCHAIN
# ====================================================
BLOCKCHAIN_DATA_DIR = "data/blockchain"
MINING_DIFFICULTY = 2  # Semakin besar, semakin lambat
TRANSACTIONS_PER_BLOCK = 10

# ====================================================
# LOGGING
# ====================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "logs/koperasi.log"

# ====================================================
# FUNGSI UNTUK MENGECEK KONFIGURASI
# ====================================================
def get_config():
    """Mengembalikan semua konfigurasi sebagai dictionary"""
    return {
        "token_per_gram": TOKEN_PER_GRAM,
        "gram_per_token": GRAM_PER_TOKEN,
        "iuran_awal": IURAN_AWAL,
        "iuran_bulanan": IURAN_BULANAN,
        "biaya_admin_persen": BIAYA_ADMIN_PERSEN,
        "modal_emas_awal_gram": MODAL_EMAS_AWAL_GRAM,
        "stok_token_awal": STOK_TOKEN_AWAL,
        "database_url": DATABASE_URL,
        "port": PORT,
        "host": HOST,
        "cache_duration": CACHE_DURATION_HARGA_EMAS,
        "mining_difficulty": MINING_DIFFICULTY,
        "transactions_per_block": TRANSACTIONS_PER_BLOCK,
        "version": "1.0.0"
    }

def validate_config():
    """Validasi konfigurasi apakah sudah benar"""
    errors = []
    
    if IURAN_AWAL <= 0:
        errors.append("Iuran awal harus positif")
    
    if IURAN_BULANAN <= 0:
        errors.append("Iuran bulanan harus positif")
    
    if BIAYA_ADMIN_PERSEN < 0 or BIAYA_ADMIN_PERSEN > 1:
        errors.append("Biaya admin harus antara 0 dan 1 (0-100%)")
    
    if MODAL_EMAS_AWAL_GRAM <= 0:
        errors.append("Modal awal emas harus positif")
    
    if errors:
        print("❌ Konfigurasi tidak valid:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    print("✅ Konfigurasi valid")
    return True

# ====================================================
# TESTING
# ====================================================
if __name__ == "__main__":
    print("=" * 50)
    print("KONFIGURASI KOPERASI TOKEN EMAS")
    print("=" * 50)
    
    validate_config()
    
    config = get_config()
    
    print(f"\n📊 RINGKASAN KONFIGURASI:")
    print(f"   Token per gram: {config['token_per_gram']}")
    print(f"   Gram per token: {config['gram_per_token']:.6f}")
    print(f"   Iuran awal: Rp {config['iuran_awal']:,}")
    print(f"   Iuran bulanan: Rp {config['iuran_bulanan']:,}")
    print(f"   Biaya admin: {config['biaya_admin_persen']*100}%")
    print(f"   Modal emas awal: {config['modal_emas_awal_gram']} gram")
    print(f"   Stok token awal: {config['stok_token_awal']} token")
    print(f"\n⚙️ LAINNYA:")
    print(f"   Database: {config['database_url']}")
    print(f"   Server: {config['host']}:{config['port']}")
    print(f"   Cache: {config['cache_duration']} detik")