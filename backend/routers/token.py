"""
Router untuk endpoint Transaksi Token (Beli & Jual)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from database import get_db, User, Anggota, Token
from utils import helpers
from utils.harga_emas import get_gold_price
from blockchain import blockchain
import config

router = APIRouter(prefix="/token", tags=["Token"])

# ====================================================
# BELI TOKEN (TOP UP)
# ====================================================
@router.post("/beli")
def beli_token(
    user_id: int,
    jumlah_rupiah: float,
    metode: str = "transfer",
    db: Session = Depends(get_db)
):
    """
    Membeli token dengan rupiah
    - Harga 1 token = Rp 500
    - Biaya admin 1% dari nilai transaksi
    - Minimal beli Rp 500 (1 token)
    """
    # Validasi
    if jumlah_rupiah < config.HARGA_PER_TOKEN:
        raise HTTPException(400, f"Minimal beli Rp {config.HARGA_PER_TOKEN}")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    # Hitung token dasar
    token_dasar = int(jumlah_rupiah / config.HARGA_PER_TOKEN)
    
    # Hitung biaya admin
    biaya_admin_rupiah = helpers.hitung_biaya_admin(jumlah_rupiah)
    biaya_admin_token = helpers.hitung_biaya_admin_token(token_dasar)
    
    # Total token yang diterima
    token_diterima = token_dasar
    
    # Buat token baru
    new_tokens = []
    for i in range(token_diterima):
        token_code = helpers.generate_token_code()
        token = Token(
            token_code=token_code,
            owner_id=user_id,
            status="active"
        )
        db.add(token)
        new_tokens.append(token_code)
    
    db.commit()
    
    # Catat ke blockchain
    blockchain.add_transaction({
        "type": "beli_token",
        "user_id": user_id,
        "username": user.username,
        "jumlah_rupiah": jumlah_rupiah,
        "token_dasar": token_dasar,
        "token_diterima": token_diterima,
        "biaya_admin_rupiah": biaya_admin_rupiah,
        "biaya_admin_token": biaya_admin_token,
        "metode": metode,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "message": f"Berhasil membeli {token_diterima} token",
        "data": {
            "user_id": user_id,
            "username": user.username,
            "jumlah_rupiah": jumlah_rupiah,
            "token_dasar": token_dasar,
            "token_diterima": token_diterima,
            "biaya_admin_rupiah": biaya_admin_rupiah,
            "biaya_admin_token": biaya_admin_token,
            "total_bayar": jumlah_rupiah + biaya_admin_rupiah,
            "formatted_bayar": helpers.format_rupiah(jumlah_rupiah + biaya_admin_rupiah),
            "token_pertama": new_tokens[:3] if new_tokens else []
        }
    }

# ====================================================
# JUAL TOKEN (WITHDRAW)
# ====================================================
@router.post("/jual")
def jual_token(
    user_id: int,
    jumlah_token: int,
    db: Session = Depends(get_db)
):
    """
    Menjual token ke koperasi (ditukar rupiah)
    - 1 token = Rp 500
    - Dipotong biaya admin 1%
    - Minimal jual 1 token
    """
    if jumlah_token < 1:
        raise HTTPException(400, "Minimal jual 1 token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    # Cek saldo token
    saldo_token = db.query(Token).filter(
        Token.owner_id == user_id,
        Token.status == "active"
    ).count()
    
    if saldo_token < jumlah_token:
        raise HTTPException(400, f"Saldo tidak cukup. Tersedia {saldo_token} token")
    
    # Hitung nilai
    nilai_dasar = jumlah_token * config.HARGA_PER_TOKEN
    biaya_admin = helpers.hitung_biaya_admin(nilai_dasar)
    nilai_diterima = nilai_dasar - biaya_admin
    
    # Ambil token untuk dijual
    tokens_to_sell = db.query(Token).filter(
        Token.owner_id == user_id,
        Token.status == "active"
    ).limit(jumlah_token).all()
    
    # Update status token
    token_codes = []
    for token in tokens_to_sell:
        token.status = "redeemed"
        token.owner_id = None
        token_codes.append(token.token_code)
    
    db.commit()
    
    # Catat ke blockchain
    blockchain.add_transaction({
        "type": "jual_token",
        "user_id": user_id,
        "username": user.username,
        "jumlah_token": jumlah_token,
        "nilai_dasar": nilai_dasar,
        "biaya_admin": biaya_admin,
        "nilai_diterima": nilai_diterima,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "message": f"Berhasil menjual {jumlah_token} token",
        "data": {
            "user_id": user_id,
            "username": user.username,
            "jumlah_token": jumlah_token,
            "nilai_dasar": nilai_dasar,
            "biaya_admin": biaya_admin,
            "nilai_diterima": nilai_diterima,
            "formatted_diterima": helpers.format_rupiah(nilai_diterima),
            "token_dijual": token_codes[:3]
        }
    }

# ====================================================
# RIWAYAT TRANSAKSI TOKEN
# ====================================================
@router.get("/riwayat/{user_id}")
def riwayat_transaksi(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Mendapatkan riwayat transaksi token user
    (Diambil dari blockchain)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    # Ambil dari blockchain
    history = blockchain.get_transaction_history(user_id=user_id)
    
    # Urutkan terbaru ke lama
    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Pagination
    paginated = history[offset:offset + limit]
    
    return {
        "user_id": user_id,
        "username": user.username,
        "total_transaksi": len(history),
        "limit": limit,
        "offset": offset,
        "data": paginated
    }

# ====================================================
# CEK NILAI TOKEN SAAT INI
# ====================================================
@router.get("/nilai")
def nilai_token():
    """
    Menampilkan nilai token saat ini
    - Harga beli
    - Harga jual
    - Setara emas
    """
    harga = get_gold_price()
    
    return {
        "harga_dasar": config.HARGA_PER_TOKEN,
        "harga_beli": config.HARGA_PER_TOKEN,  # Beli = harga dasar
        "harga_jual": config.HARGA_PER_TOKEN,  # Jual = harga dasar - admin
        "biaya_admin_persen": config.BIAYA_ADMIN_PERSEN * 100,
        "setara_gram": config.GRAM_PER_TOKEN,
        "nilai_emas": config.GRAM_PER_TOKEN * harga["price_idr_per_gram"],
        "formatted_nilai_emas": helpers.format_rupiah(config.GRAM_PER_TOKEN * harga["price_idr_per_gram"]),
        "harga_emas": {
            "per_gram": harga["price_idr_per_gram"],
            "formatted": helpers.format_rupiah(harga["price_idr_per_gram"])
        }
    }

# ====================================================
# CEK SALDO TOKEN (SUDAH ADA DI users.py)
# (Tidak perlu dibuat ulang)
# ====================================================