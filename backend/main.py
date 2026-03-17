"""
Main Entry Point untuk Backend Koperasi Token Emas
FastAPI Server
"""

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import uvicorn

# Import konfigurasi
import config

# Import database
from database import init_db, get_db, User, Anggota, Token, StokToken, EmasFisik, TransaksiIuran, TransaksiToken

# Import blockchain
from blockchain import blockchain

# Import utils
from utils import helpers
from utils.harga_emas import get_gold_price, get_historical_prices, get_kurs_historical

# Import routers
from routers import admin

# Inisialisasi database
init_db()

# Buat aplikasi FastAPI
app = FastAPI(
    title="Koperasi Token Emas API",
    description="Backend untuk sistem koperasi token emas",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ====================================================
# CORS MIDDLEWARE
# ====================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Untuk development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================================================
# REGISTER ROUTERS
# ====================================================
app.include_router(admin.router)

# ====================================================
# FUNGSI BANTUAN
# ====================================================
def get_stok_token(db: Session):
    """Mendapatkan jumlah stok token saat ini"""
    stok = db.query(StokToken).order_by(StokToken.created_at.desc()).first()
    return stok.jumlah if stok else 0

def update_stok_token(db: Session, perubahan: int, keterangan: str):
    """Update stok token dan catat di blockchain"""
    stok = db.query(StokToken).order_by(StokToken.created_at.desc()).first()
    if not stok:
        stok = StokToken(jumlah=config.STOK_TOKEN_AWAL)
        db.add(stok)
    
    stok.jumlah += perubahan
    db.commit()
    
    blockchain.add_transaction({
        "type": "stok_update",
        "perubahan": perubahan,
        "stok_baru": stok.jumlah,
        "keterangan": keterangan
    })
    
    return stok.jumlah

def potong_iuran_bulanan(background_tasks: BackgroundTasks, db: Session):
    """Background task untuk memotong iuran semua anggota setiap tanggal 1"""
    anggota_aktif = db.query(Anggota).filter(Anggota.status == "aktif").all()
    
    for anggota in anggota_aktif:
        if anggota.saldo_iuran >= config.IURAN_BULANAN:
            saldo_sebelum = anggota.saldo_iuran
            anggota.saldo_iuran -= config.IURAN_BULANAN
            saldo_sesudah = anggota.saldo_iuran
            
            transaksi = TransaksiIuran(
                anggota_id=anggota.id,
                jenis="potong_bulanan",
                jumlah=config.IURAN_BULANAN,
                saldo_sebelum=saldo_sebelum,
                saldo_sesudah=saldo_sesudah,
                keterangan=f"Potongan iuran bulan {datetime.now().strftime('%B %Y')}"
            )
            db.add(transaksi)
            
            if anggota.saldo_iuran < config.IURAN_BULANAN:
                anggota.status = "nonaktif"
                # Kirim notifikasi nanti
        else:
            anggota.status = "nonaktif"
    
    db.commit()

# ====================================================
# ENDPOINT UTAMA
# ====================================================
@app.get("/")
def root():
    return {
        "message": "🚀 Koperasi Token Emas API",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/info")
def info_koperasi(db: Session = Depends(get_db)):
    """Info publik koperasi"""
    total_anggota = db.query(Anggota).filter(Anggota.status == "aktif").count()
    stok_token = get_stok_token(db)
    
    emas_list = db.query(EmasFisik).all()
    total_gram = sum(e.jumlah_gram for e in emas_list)
    
    harga = get_gold_price()
    
    return {
        "nama": "Koperasi Token Emas",
        "statistik": {
            "total_anggota_aktif": total_anggota,
            "stok_token": stok_token,
            "total_emas_fisik": f"{total_gram:.2f} gram",
            "nilai_emas": helpers.format_rupiah(total_gram * harga["price_idr_per_gram"])
        },
        "iuran": {
            "awal": config.IURAN_AWAL,
            "bulanan": config.IURAN_BULANAN
        },
        "harga_emas": {
            "per_gram": harga["price_idr_per_gram"],
            "nilai_per_token": harga["nilai_per_token"],
            "formatted": helpers.format_rupiah(harga["price_idr_per_gram"])
        }
    }

@app.get("/harga")
def get_harga():
    """Endpoint harga emas realtime"""
    harga = get_gold_price()
    return {
        "emas": {
            "per_gram": harga["price_idr_per_gram"],
            "nilai_per_token": harga["nilai_per_token"],
            "formatted": helpers.format_rupiah(harga["price_idr_per_gram"])
        },
        "kurs": {
            "usd_to_idr": harga["usd_to_idr"],
            "formatted": "Rp " + helpers.format_rupiah(harga["usd_to_idr"]).replace('Rp ', '')
        }
    }

@app.get("/historical")
def get_historical(days: int = 7):
    """
    Mendapatkan data historis harga emas, nilai token, dan kurs
    untuk grafik 7 hari terakhir
    """
    emas = get_historical_prices(days)
    kurs = get_kurs_historical(days)
    
    # Gabungkan data
    result = []
    for i in range(days):
        date_obj = datetime.strptime(emas[i]["date"], "%Y-%m-%d")
        result.append({
            "date": emas[i]["date"],
            "date_display": date_obj.strftime("%d %b"),
            "emas": emas[i]["price"],
            "token": round(emas[i]["price"] / 2000, 2),  # Nilai token dari harga emas
            "kurs": kurs[i]["kurs"]
        })
    
    return result

# ====================================================
# ENDPOINT USER
# ====================================================
@app.post("/user/register")
def register_user(
    username: str,
    email: str,
    full_name: str,
    db: Session = Depends(get_db)
):
    """Registrasi user baru"""
    if not helpers.validasi_username(username):
        raise HTTPException(400, "Username tidak valid")
    
    if not helpers.validasi_email(email):
        raise HTTPException(400, "Email tidak valid")
    
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "Username sudah digunakan")
    
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email sudah terdaftar")
    
    user = User(
        user_id=helpers.generate_user_id(),
        username=username,
        email=email,
        full_name=full_name,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "data": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name
        }
    }

@app.post("/anggota/daftar")
def daftar_anggota(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Daftar jadi anggota (bayar iuran awal Rp 12.000)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    if db.query(Anggota).filter(Anggota.user_id == user_id).first():
        raise HTTPException(400, "User sudah menjadi anggota")
    
    # Buat anggota baru
    nomor_anggota = helpers.generate_nomor_anggota()
    anggota = Anggota(
        user_id=user_id,
        nomor_anggota=nomor_anggota,
        status="aktif",
        saldo_iuran=config.IURAN_AWAL
    )
    db.add(anggota)
    db.flush()
    
    # Catat transaksi iuran
    transaksi = TransaksiIuran(
        anggota_id=anggota.id,
        jenis="daftar",
        jumlah=config.IURAN_AWAL,
        saldo_sebelum=0,
        saldo_sesudah=config.IURAN_AWAL,
        keterangan="Pendaftaran anggota baru"
    )
    db.add(transaksi)
    
    db.commit()
    
    blockchain.add_transaction({
        "type": "anggota_baru",
        "user_id": user_id,
        "nomor_anggota": nomor_anggota,
        "iuran_awal": config.IURAN_AWAL
    })
    
    return {
        "success": True,
        "message": "Selamat! Anda resmi menjadi anggota",
        "data": {
            "nomor_anggota": nomor_anggota,
            "saldo_iuran": config.IURAN_AWAL,
            "status": "aktif"
        }
    }

@app.get("/anggota/{nomor_anggota}/status")
def cek_status_anggota(nomor_anggota: str, db: Session = Depends(get_db)):
    """Cek status anggota dan saldo iuran"""
    anggota = db.query(Anggota).filter(Anggota.nomor_anggota == nomor_anggota).first()
    if not anggota:
        raise HTTPException(404, "Anggota tidak ditemukan")
    
    user = db.query(User).filter(User.id == anggota.user_id).first()
    harga = get_gold_price()
    
    # Hitung nilai wallet
    nilai_wallet = anggota.token_sukarela * harga["nilai_per_token"]
    
    # Cek sisa bulan iuran
    sisa_bulan = anggota.saldo_iuran // config.IURAN_BULANAN
    
    return {
        "nomor_anggota": anggota.nomor_anggota,
        "nama": user.full_name,
        "status": anggota.status,
        "saldo_iuran": anggota.saldo_iuran,
        "sisa_bulan": int(sisa_bulan),
        "token": {
            "jumlah": anggota.token_sukarela,
            "nilai_per_token": harga["nilai_per_token"],
            "total_nilai": nilai_wallet,
            "formatted_nilai": helpers.format_rupiah(nilai_wallet)
        }
    }

@app.post("/anggota/topup-iuran")
def topup_iuran(
    nomor_anggota: str,
    jumlah: float,
    db: Session = Depends(get_db)
):
    """Top up saldo iuran (minimal Rp 12.000)"""
    if jumlah < config.IURAN_AWAL:
        raise HTTPException(400, f"Minimal top up Rp {config.IURAN_AWAL}")
    
    anggota = db.query(Anggota).filter(Anggota.nomor_anggota == nomor_anggota).first()
    if not anggota:
        raise HTTPException(404, "Anggota tidak ditemukan")
    
    saldo_sebelum = anggota.saldo_iuran
    anggota.saldo_iuran += jumlah
    
    if anggota.status == "nonaktif" and anggota.saldo_iuran >= config.IURAN_BULANAN:
        anggota.status = "aktif"
    
    transaksi = TransaksiIuran(
        anggota_id=anggota.id,
        jenis="topup",
        jumlah=jumlah,
        saldo_sebelum=saldo_sebelum,
        saldo_sesudah=anggota.saldo_iuran
    )
    db.add(transaksi)
    db.commit()
    
    return {
        "success": True,
        "message": "Top up iuran berhasil",
        "data": {
            "saldo_iuran": anggota.saldo_iuran,
            "status": anggota.status
        }
    }

@app.post("/token/beli")
def beli_token(
    nomor_anggota: str,
    jumlah_token: int,
    db: Session = Depends(get_db)
):
    """Anggota beli token dari stok koperasi"""
    if jumlah_token <= 0:
        raise HTTPException(400, "Jumlah token harus positif")
    
    anggota = db.query(Anggota).filter(Anggota.nomor_anggota == nomor_anggota).first()
    if not anggota:
        raise HTTPException(404, "Anggota tidak ditemukan")
    
    if anggota.status != "aktif":
        raise HTTPException(400, "Anggota tidak aktif. Silakan top up iuran")
    
    # Cek stok token
    stok = get_stok_token(db)
    if stok < jumlah_token:
        raise HTTPException(400, f"Stok token tidak cukup. Tersedia {stok}")
    
    # Hitung harga (dasar Rp 500/token untuk beli)
    harga_dasar = jumlah_token * 500
    biaya_admin = helpers.hitung_biaya_admin_rupiah(harga_dasar, config.BIAYA_ADMIN_PERSEN)
    total_bayar = harga_dasar + biaya_admin
    
    # Catat transaksi
    token_sebelum = anggota.token_sukarela
    anggota.token_sukarela += jumlah_token
    
    transaksi = TransaksiToken(
        anggota_id=anggota.id,
        jenis="beli",
        jumlah_token=jumlah_token,
        harga_emas_saat_transaksi=get_gold_price()["price_idr_per_gram"],
        nilai_rupiah=harga_dasar,
        biaya_admin=biaya_admin,
        token_sebelum=token_sebelum,
        token_sesudah=anggota.token_sukarela
    )
    db.add(transaksi)
    
    # Update stok token
    update_stok_token(db, -jumlah_token, f"Pembelian oleh {anggota.nomor_anggota}")
    
    db.commit()
    
    blockchain.add_transaction({
        "type": "beli_token",
        "anggota_id": anggota.id,
        "nomor_anggota": nomor_anggota,
        "jumlah_token": jumlah_token,
        "harga_dasar": harga_dasar,
        "biaya_admin": biaya_admin,
        "total_bayar": total_bayar
    })
    
    return {
        "success": True,
        "message": f"Berhasil membeli {jumlah_token} token",
        "data": {
            "jumlah_token": jumlah_token,
            "harga_dasar": harga_dasar,
            "biaya_admin": biaya_admin,
            "total_bayar": total_bayar,
            "token_sekarang": anggota.token_sukarela
        }
    }

@app.post("/token/jual")
def jual_token(
    nomor_anggota: str,
    jumlah_token: int,
    db: Session = Depends(get_db)
):
    """Anggota jual token ke koperasi"""
    if jumlah_token <= 0:
        raise HTTPException(400, "Jumlah token harus positif")
    
    anggota = db.query(Anggota).filter(Anggota.nomor_anggota == nomor_anggota).first()
    if not anggota:
        raise HTTPException(404, "Anggota tidak ditemukan")
    
    if anggota.status != "aktif":
        raise HTTPException(400, "Anggota tidak aktif")
    
    if anggota.token_sukarela < jumlah_token:
        raise HTTPException(400, f"Token tidak cukup. Anda punya {anggota.token_sukarela}")
    
    # Hitung nilai jual berdasarkan harga emas update
    harga_emas = get_gold_price()
    nilai_per_token = harga_emas["nilai_per_token"]
    nilai_jual = jumlah_token * nilai_per_token
    biaya_admin = helpers.hitung_biaya_admin_rupiah(nilai_jual, config.BIAYA_ADMIN_PERSEN)
    total_diterima = nilai_jual - biaya_admin
    
    # Catat transaksi
    token_sebelum = anggota.token_sukarela
    anggota.token_sukarela -= jumlah_token
    
    transaksi = TransaksiToken(
        anggota_id=anggota.id,
        jenis="jual",
        jumlah_token=jumlah_token,
        harga_emas_saat_transaksi=harga_emas["price_idr_per_gram"],
        nilai_rupiah=nilai_jual,
        biaya_admin=biaya_admin,
        token_sebelum=token_sebelum,
        token_sesudah=anggota.token_sukarela
    )
    db.add(transaksi)
    
    # Update stok token
    update_stok_token(db, jumlah_token, f"Penjualan oleh {anggota.nomor_anggota}")
    
    db.commit()
    
    blockchain.add_transaction({
        "type": "jual_token",
        "anggota_id": anggota.id,
        "nomor_anggota": nomor_anggota,
        "jumlah_token": jumlah_token,
        "nilai_jual": nilai_jual,
        "biaya_admin": biaya_admin,
        "total_diterima": total_diterima
    })
    
    return {
        "success": True,
        "message": f"Berhasil menjual {jumlah_token} token",
        "data": {
            "jumlah_token": jumlah_token,
            "nilai_per_token": nilai_per_token,
            "nilai_jual": nilai_jual,
            "biaya_admin": biaya_admin,
            "total_diterima": total_diterima,
            "token_sekarang": anggota.token_sukarela
        }
    }

@app.post("/transfer")
def transfer_token(
    dari_nomor: str,
    ke_nomor: str,
    jumlah_token: int,
    db: Session = Depends(get_db)
):
    """Transfer token antar anggota (GRATIS)"""
    if jumlah_token <= 0:
        raise HTTPException(400, "Jumlah token harus positif")
    
    pengirim = db.query(Anggota).filter(Anggota.nomor_anggota == dari_nomor).first()
    if not pengirim:
        raise HTTPException(404, "Pengirim tidak ditemukan")
    
    penerima = db.query(Anggota).filter(Anggota.nomor_anggota == ke_nomor).first()
    if not penerima:
        raise HTTPException(404, "Penerima tidak ditemukan")
    
    if pengirim.status != "aktif" or penerima.status != "aktif":
        raise HTTPException(400, "Kedua anggota harus aktif")
    
    if pengirim.token_sukarela < jumlah_token:
        raise HTTPException(400, f"Token pengirim tidak cukup")
    
    # Proses transfer
    token_pengirim_sebelum = pengirim.token_sukarela
    token_penerima_sebelum = penerima.token_sukarela
    
    pengirim.token_sukarela -= jumlah_token
    penerima.token_sukarela += jumlah_token
    
    # Catat transaksi pengirim
    transaksi_keluar = TransaksiToken(
        anggota_id=pengirim.id,
        jenis="transfer_keluar",
        jumlah_token=jumlah_token,
        harga_emas_saat_transaksi=get_gold_price()["price_idr_per_gram"],
        token_sebelum=token_pengirim_sebelum,
        token_sesudah=pengirim.token_sukarela,
        keterangan=f"Transfer ke {ke_nomor}"
    )
    db.add(transaksi_keluar)
    
    # Catat transaksi penerima
    transaksi_masuk = TransaksiToken(
        anggota_id=penerima.id,
        jenis="transfer_masuk",
        jumlah_token=jumlah_token,
        harga_emas_saat_transaksi=get_gold_price()["price_idr_per_gram"],
        token_sebelum=token_penerima_sebelum,
        token_sesudah=penerima.token_sukarela,
        keterangan=f"Transfer dari {dari_nomor}"
    )
    db.add(transaksi_masuk)
    
    db.commit()
    
    blockchain.add_transaction({
        "type": "transfer",
        "dari": dari_nomor,
        "ke": ke_nomor,
        "jumlah_token": jumlah_token
    })
    
    return {
        "success": True,
        "message": "Transfer berhasil",
        "data": {
            "dari": dari_nomor,
            "ke": ke_nomor,
            "jumlah_token": jumlah_token
        }
    }

@app.get("/user/{user_id}/saldo")
def cek_saldo_user(user_id: int, db: Session = Depends(get_db)):
    """Cek saldo token user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    anggota = db.query(Anggota).filter(Anggota.user_id == user_id).first()
    harga = get_gold_price()
    
    if not anggota:
        return {
            "user_id": user.id,
            "full_name": user.full_name,
            "status": "non_anggota",
            "token": 0,
            "nilai_token": 0
        }
    
    nilai_token = anggota.token_sukarela * harga["nilai_per_token"]
    
    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "nomor_anggota": anggota.nomor_anggota,
        "status": anggota.status,
        "saldo_iuran": anggota.saldo_iuran,
        "token": anggota.token_sukarela,
        "nilai_per_token": harga["nilai_per_token"],
        "total_nilai_token": nilai_token,
        "formatted_nilai": helpers.format_rupiah(nilai_token)
    }

# ====================================================
# JALANKAN SERVER
# ====================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 SERVER KOPERASI TOKEN EMAS")
    print("=" * 60)
    print(f"Menjalankan server di http://{config.HOST}:{config.PORT}")
    print(f"Dokumentasi API: http://{config.HOST}:{config.PORT}/docs")
    print(f"Info publik: http://{config.HOST}:{config.PORT}/info")
    print(f"Data historis: http://{config.HOST}:{config.PORT}/historical")
    print("\nTekan Ctrl+C untuk menghentikan server")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True
    )