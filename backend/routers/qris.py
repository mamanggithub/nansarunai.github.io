"""
Router untuk endpoint Pembayaran QRIS
- Pembeli bayar +1% dari nilai transaksi
- Pedagang terima -1% dari nilai transaksi
- Minimal transaksi Rp 500 (1 token)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from database import get_db, User, Anggota, Token
from utils import helpers
from blockchain import blockchain
import config

router = APIRouter(prefix="/qris", tags=["QRIS"])

# ====================================================
# GENERATE QR CODE DATA
# ====================================================
@router.get("/generate/{user_id}")
def generate_qr_data(user_id: int, db: Session = Depends(get_db)):
    """
    Generate data untuk QR code pedagang
    Format: KOPERASI:user_id:nama
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    # Cek apakah anggota aktif
    anggota = db.query(Anggota).filter(
        Anggota.user_id == user_id,
        Anggota.status == "aktif"
    ).first()
    
    if not anggota:
        raise HTTPException(400, "User bukan anggota aktif")
    
    qr_data = helpers.generate_qr_code_data(user_id, user.full_name)
    
    return {
        "user_id": user_id,
        "nama": user.full_name,
        "qr_data": qr_data,
        "nomor_anggota": anggota.nomor_anggota
    }

# ====================================================
# PARSE QR CODE
# ====================================================
@router.post("/parse")
def parse_qr_data(qr_data: str):
    """
    Parse data dari QR code
    """
    user_id, nama = helpers.parse_qr_code_data(qr_data)
    
    if user_id is None:
        raise HTTPException(400, "QR Code tidak valid")
    
    return {
        "valid": True,
        "user_id": user_id,
        "nama": nama
    }

# ====================================================
# PEMBAYARAN VIA QRIS
# ====================================================
@router.post("/bayar")
def bayar_qris(
    pembeli_id: int,
    qr_data: str,
    jumlah_rupiah: float,
    catatan: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Pembayaran menggunakan QRIS
    - Pembeli bayar: nilai + 1% admin
    - Pedagang terima: nilai - 1% admin
    - Minimal transaksi Rp 500
    """
    # Validasi QR
    pedagang_id, pedagang_nama = helpers.parse_qr_code_data(qr_data)
    if pedagang_id is None:
        raise HTTPException(400, "QR Code tidak valid")
    
    # Validasi nominal
    if jumlah_rupiah < config.HARGA_PER_TOKEN:
        raise HTTPException(400, f"Minimal transaksi Rp {config.HARGA_PER_TOKEN}")
    
    # Cek pembeli
    pembeli = db.query(User).filter(User.id == pembeli_id).first()
    if not pembeli:
        raise HTTPException(404, "Pembeli tidak ditemukan")
    
    # Cek pedagang
    pedagang = db.query(User).filter(User.id == pedagang_id).first()
    if not pedagang:
        raise HTTPException(404, "Pedagang tidak ditemukan")
    
    # Cek status anggota
    pembeli_anggota = db.query(Anggota).filter(
        Anggota.user_id == pembeli_id,
        Anggota.status == "aktif"
    ).first()
    
    if not pembeli_anggota:
        raise HTTPException(400, "Pembeli bukan anggota aktif")
    
    pedagang_anggota = db.query(Anggota).filter(
        Anggota.user_id == pedagang_id,
        Anggota.status == "aktif"
    ).first()
    
    if not pedagang_anggota:
        raise HTTPException(400, "Pedagang bukan anggota aktif")
    
    # Hitung token dasar
    token_dasar = int(jumlah_rupiah / config.HARGA_PER_TOKEN)
    
    # Biaya admin (pembeli +1%, pedagang -1%)
    biaya_admin_pembeli = helpers.hitung_biaya_admin_token(token_dasar)
    biaya_admin_pedagang = helpers.hitung_biaya_admin_token(token_dasar)
    
    # Total token yang harus dibayar pembeli
    total_pembeli_bayar = token_dasar + biaya_admin_pembeli
    
    # Total token yang diterima pedagang
    total_pedagang_terima = token_dasar - biaya_admin_pedagang
    
    if total_pedagang_terima < 0:
        raise HTTPException(400, "Nilai transaksi terlalu kecil setelah dipotong admin")
    
    # Cek saldo pembeli
    saldo_pembeli = db.query(Token).filter(
        Token.owner_id == pembeli_id,
        Token.status == "active"
    ).count()
    
    if saldo_pembeli < total_pembeli_bayar:
        raise HTTPException(
            400,
            f"Saldo pembeli tidak cukup. Butuh {total_pembeli_bayar} token, saldo {saldo_pembeli}"
        )
    
    # Ambil token pembeli
    tokens_pembeli = db.query(Token).filter(
        Token.owner_id == pembeli_id,
        Token.status == "active"
    ).limit(total_pembeli_bayar).all()
    
    # Bagi token:
    # - token_dasar untuk pedagang
    # - biaya_admin_pembeli untuk koperasi
    # - biaya_admin_pedagang juga untuk koperasi
    token_pedagang = tokens_pembeli[:token_dasar]
    token_admin1 = tokens_pembeli[token_dasar:token_dasar + biaya_admin_pembeli]
    token_admin2 = tokens_pembeli[token_dasar + biaya_admin_pembeli:]
    
    # Update kepemilikan
    for token in token_pedagang:
        token.owner_id = pedagang_id
    
    for token in token_admin1 + token_admin2:
        token.owner_id = None
        token.status = "koperasi"
    
    total_admin_token = biaya_admin_pembeli + biaya_admin_pedagang
    total_admin_rupiah = total_admin_token * config.HARGA_PER_TOKEN
    
    db.commit()
    
    # Catat ke blockchain
    blockchain.add_transaction({
        "type": "qris_payment",
        "pembeli_id": pembeli_id,
        "pembeli_nama": pembeli.full_name,
        "pedagang_id": pedagang_id,
        "pedagang_nama": pedagang.full_name,
        "jumlah_rupiah": jumlah_rupiah,
        "token_dasar": token_dasar,
        "pembeli_bayar": {
            "token": total_pembeli_bayar,
            "rupiah": total_pembeli_bayar * config.HARGA_PER_TOKEN
        },
        "pedagang_terima": {
            "token": total_pedagang_terima,
            "rupiah": total_pedagang_terima * config.HARGA_PER_TOKEN
        },
        "koperasi_dapat": {
            "token": total_admin_token,
            "rupiah": total_admin_rupiah
        },
        "catatan": catatan,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "message": "Pembayaran berhasil",
        "data": {
            "pembeli": {
                "id": pembeli_id,
                "nama": pembeli.full_name
            },
            "pedagang": {
                "id": pedagang_id,
                "nama": pedagang.full_name,
                "nomor_anggota": pedagang_anggota.nomor_anggota
            },
            "transaksi": {
                "nilai_belanja": jumlah_rupiah,
                "formatted_belanja": helpers.format_rupiah(jumlah_rupiah),
                "token_dasar": token_dasar,
                "pembeli_bayar_token": total_pembeli_bayar,
                "pembeli_bayar_rupiah": total_pembeli_bayar * config.HARGA_PER_TOKEN,
                "pedagang_terima_token": total_pedagang_terima,
                "pedagang_terima_rupiah": total_pedagang_terima * config.HARGA_PER_TOKEN,
                "koperasi_dapat_token": total_admin_token,
                "koperasi_dapat_rupiah": total_admin_rupiah,
                "formatted_koperasi": helpers.format_rupiah(total_admin_rupiah)
            },
            "catatan": catatan
        }
    }

# ====================================================
# HITUNG BIAYA QRIS
# ====================================================
@router.get("/hitung-biaya")
def hitung_biaya_qris(jumlah_rupiah: float):
    """
    Menghitung biaya transaksi QRIS
    """
    if jumlah_rupiah < config.HARGA_PER_TOKEN:
        return {
            "error": True,
            "message": f"Minimal transaksi Rp {config.HARGA_PER_TOKEN}"
        }
    
    token_dasar = int(jumlah_rupiah / config.HARGA_PER_TOKEN)
    biaya_pembeli = helpers.hitung_biaya_admin_token(token_dasar)
    biaya_pedagang = helpers.hitung_biaya_admin_token(token_dasar)
    
    return {
        "jumlah_rupiah": jumlah_rupiah,
        "formatted_rupiah": helpers.format_rupiah(jumlah_rupiah),
        "token_dasar": token_dasar,
        "biaya_admin": {
            "pembeli_token": biaya_pembeli,
            "pembeli_rupiah": biaya_pembeli * config.HARGA_PER_TOKEN,
            "pedagang_token": biaya_pedagang,
            "pedagang_rupiah": biaya_pedagang * config.HARGA_PER_TOKEN,
            "total_token": biaya_pembeli + biaya_pedagang,
            "total_rupiah": (biaya_pembeli + biaya_pedagang) * config.HARGA_PER_TOKEN,
            "formatted_total": helpers.format_rupiah((biaya_pembeli + biaya_pedagang) * config.HARGA_PER_TOKEN)
        },
        "pembeli_bayar": {
            "token": token_dasar + biaya_pembeli,
            "rupiah": (token_dasar + biaya_pembeli) * config.HARGA_PER_TOKEN,
            "formatted": helpers.format_rupiah((token_dasar + biaya_pembeli) * config.HARGA_PER_TOKEN)
        },
        "pedagang_terima": {
            "token": token_dasar - biaya_pedagang,
            "rupiah": (token_dasar - biaya_pedagang) * config.HARGA_PER_TOKEN,
            "formatted": helpers.format_rupiah((token_dasar - biaya_pedagang) * config.HARGA_PER_TOKEN)
        }
    }

# ====================================================
# RIWAYAT TRANSAKSI QRIS
# ====================================================
@router.get("/riwayat/{user_id}")
def riwayat_qris(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Mendapatkan riwayat transaksi QRIS user
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    # Ambil dari blockchain, filter jenis qris
    all_history = blockchain.get_transaction_history(user_id=user_id)
    qris_history = [t for t in all_history if t.get("type") == "qris_payment"]
    
    # Urutkan terbaru
    qris_history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Pagination
    paginated = qris_history[offset:offset + limit]
    
    return {
        "user_id": user_id,
        "username": user.username,
        "total_transaksi_qris": len(qris_history),
        "limit": limit,
        "offset": offset,
        "data": paginated
    }

# ====================================================
# CEK SALDO SEBELUM QRIS
# ====================================================
@router.get("/cek-saldo/{pembeli_id}")
def cek_saldo_qris(
    pembeli_id: int,
    jumlah_rupiah: float,
    db: Session = Depends(get_db)
):
    """
    Cek apakah pembeli memiliki saldo cukup untuk transaksi QRIS
    """
    pembeli = db.query(User).filter(User.id == pembeli_id).first()
    if not pembeli:
        raise HTTPException(404, "Pembeli tidak ditemukan")
    
    # Hitung token yang diperlukan
    token_dasar = int(jumlah_rupiah / config.HARGA_PER_TOKEN)
    biaya_pembeli = helpers.hitung_biaya_admin_token(token_dasar)
    total_diperlukan = token_dasar + biaya_pembeli
    
    # Cek saldo
    saldo = db.query(Token).filter(
        Token.owner_id == pembeli_id,
        Token.status == "active"
    ).count()
    
    return {
        "pembeli_id": pembeli_id,
        "pembeli_nama": pembeli.full_name,
        "jumlah_rupiah": jumlah_rupiah,
        "formatted_rupiah": helpers.format_rupiah(jumlah_rupiah),
        "token_dasar": token_dasar,
        "biaya_admin": biaya_pembeli,
        "total_token_diperlukan": total_diperlukan,
        "saldo_token": saldo,
        "cukup": saldo >= total_diperlukan,
        "kekurangan": max(0, total_diperlukan - saldo) if saldo < total_diperlukan else 0
    }