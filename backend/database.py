"""
Database models untuk Koperasi Token Emas
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Buat folder data jika belum ada
os.makedirs("data", exist_ok=True)

# Database URL (SQLite untuk development)
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/koperasi.db"

# Buat engine database
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Hanya untuk SQLite
)

# Session local untuk transaksi
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class untuk model
Base = declarative_base()

# ====================================================
# TABEL USER
# ====================================================
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)  # ID unik untuk QR
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String, default="")  # Untuk nanti kalau pakai login
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)  # Apakah admin?
    created_at = Column(DateTime, default=datetime.now)
    
    # Relasi
    anggota = relationship("Anggota", back_populates="user", uselist=False)
    
    def __repr__(self):
        return f"<User {self.username}>"

# ====================================================
# TABEL ANGGOTA KOPERASI
# ====================================================
class Anggota(Base):
    __tablename__ = "anggota"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    nomor_anggota = Column(String, unique=True, index=True)  # KTA-2026-0001
    
    # Status
    status = Column(String, default="aktif")  # aktif, nonaktif
    
    # Iuran (dalam rupiah, bukan token)
    saldo_iuran = Column(Float, default=0)  # Saldo iuran dalam rupiah
    
    # Wallet token (jumlah token, nilainya mengikuti harga emas)
    token_sukarela = Column(Integer, default=0)  # Token yang dimiliki
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relasi
    user = relationship("User", back_populates="anggota")
    transaksi_iuran = relationship("TransaksiIuran", back_populates="anggota")
    transaksi_token = relationship("TransaksiToken", back_populates="anggota")
    
    def __repr__(self):
        return f"<Anggota {self.nomor_anggota}>"

# ====================================================
# TABEL TOKEN (UNTUK TRACKING INDIVIDUAL)
# ====================================================
class Token(Base):
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token_code = Column(String, unique=True, index=True)  # EMAS-20260316-ABC123
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null = milik koperasi
    status = Column(String, default="active")  # active, redeemed, stok
    issued_at = Column(DateTime, default=datetime.now)
    redeemed_at = Column(DateTime, nullable=True)
    
    # Relasi
    owner = relationship("User")

# ====================================================
# TABEL STOK TOKEN (UNTUK TRACKING STOK KESELURUHAN)
# ====================================================
class StokToken(Base):
    __tablename__ = "stok_token"
    
    id = Column(Integer, primary_key=True, index=True)
    jumlah = Column(Integer, default=0)  # Jumlah token dalam stok
    emas_gram = Column(Float, nullable=True)  # Emas yang menjadi cadangan
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<StokToken {self.jumlah} token>"

# ====================================================
# TABEL EMAS FISIK (RIWAYAT PENAMBAHAN EMAS)
# ====================================================
class EmasFisik(Base):
    __tablename__ = "emas_fisik"
    
    id = Column(Integer, primary_key=True, index=True)
    jumlah_gram = Column(Float)
    sumber = Column(String)  # "modal_awal", "laba", "dari_kas", "investasi"
    keterangan = Column(Text, nullable=True)
    harga_per_gram = Column(Float, nullable=True)  # Harga saat beli
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<EmasFisik +{self.jumlah_gram}gr dari {self.sumber}>"

# ====================================================
# TABEL TRANSAKSI IURAN (RIWAYAT IURAN ANGGOTA)
# ====================================================
class TransaksiIuran(Base):
    __tablename__ = "transaksi_iuran"
    
    id = Column(Integer, primary_key=True, index=True)
    anggota_id = Column(Integer, ForeignKey("anggota.id"))
    jenis = Column(String)  # "daftar", "topup", "potong_bulanan"
    jumlah = Column(Float)  # Dalam rupiah
    saldo_sebelum = Column(Float)
    saldo_sesudah = Column(Float)
    keterangan = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relasi
    anggota = relationship("Anggota", back_populates="transaksi_iuran")
    
    def __repr__(self):
        return f"<TransaksiIuran {self.jenis} Rp{self.jumlah}>"

# ====================================================
# TABEL TRANSAKSI TOKEN (RIWAYAT TOKEN ANGGOTA)
# ====================================================
class TransaksiToken(Base):
    __tablename__ = "transaksi_token"
    
    id = Column(Integer, primary_key=True, index=True)
    anggota_id = Column(Integer, ForeignKey("anggota.id"))
    jenis = Column(String)  # "beli", "jual", "transfer_keluar", "transfer_masuk"
    jumlah_token = Column(Integer)
    harga_emas_saat_transaksi = Column(Float)  # Harga emas per gram saat transaksi
    nilai_rupiah = Column(Float)  # Nilai transaksi dalam rupiah
    biaya_admin = Column(Float, default=0)
    token_sebelum = Column(Integer)
    token_sesudah = Column(Integer)
    keterangan = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relasi
    anggota = relationship("Anggota", back_populates="transaksi_token")
    
    def __repr__(self):
        return f"<TransaksiToken {self.jenis} {self.jumlah_token} token>"

# ====================================================
# FUNGSI INISIALISASI DATABASE
# ====================================================
def init_db():
    """Buat semua tabel di database"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database berhasil diinisialisasi!")

# ====================================================
# FUNGSI GET DB (untuk dependency FastAPI)
# ====================================================
def get_db():
    """Dapatkan session database (untuk FastAPI)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ====================================================
# JALANKAN INISIALISASI JIKA FILE DI-RUN LANGSUNG
# ====================================================
if __name__ == "__main__":
    print("=" * 50)
    print("MEMBUAT DATABASE KOPERASI")
    print("=" * 50)
    init_db()
    print("✅ Selesai!")