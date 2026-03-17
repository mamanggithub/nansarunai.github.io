"""
Router untuk endpoint Anggota Koperasi
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

router = APIRouter(prefix="/anggota", tags=["Anggota"])

# ====================================================
# DAFTAR ANGGOTA BARU (Iuran Pokok Rp 5.000)
# ====================================================
@router.post("/daftar")
def daftar_anggota(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Daftar menjadi anggota koperasi (bayar iuran pokok Rp 5.000)
    """
    # Cek user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    # Cek sudah jadi anggota?
    if db.query(Anggota).filter(Anggota.user_id == user_id).first():
        raise HTTPException(400, "User sudah terdaftar sebagai anggota")
    
    # Buat anggota baru
    nomor_anggota = helpers.generate_nomor_anggota()
    anggota = Anggota(
        user_id=user_id,
        nomor_anggota=nomor_anggota,
        status="aktif",
        iuran_pokok_rupiah=config.IURAN_POKOK_RUPIAH,
        iuran_pokok_token=config.IURAN_POKOK_TOKEN,
        iuran_pokok_lunas=True,
        tanggal_bayar_pokok=datetime.now(),
        iuran_wajib_bulanan=config.IURAN_WAJIB_RUPIAH,
        iuran_wajib_token=config.IURAN_WAJIB_TOKEN,
        total_setoran_rupiah=config.IURAN_POKOK_RUPIAH
    )
    
    db.add(anggota)
    db.flush()
    
    # Buat token untuk anggota
    new_tokens = []
    for i in range(config.IURAN_POKOK_TOKEN):
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
        "type": "anggota_baru",
        "user_id": user_id,
        "nomor_anggota": nomor_anggota,
        "iuran_rupiah": config.IURAN_POKOK_RUPIAH,
        "token_diterbitkan": config.IURAN_POKOK_TOKEN,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "message": "Selamat! Anda resmi menjadi anggota koperasi",
        "data": {
            "nomor_anggota": nomor_anggota,
            "nama": user.full_name,
            "token_didapat": config.IURAN_POKOK_TOKEN,
            "iuran_pokok": helpers.format_rupiah(config.IURAN_POKOK_RUPIAH)
        }
    }

# ====================================================
# CEK STATUS ANGGOTA
# ====================================================
@router.get("/{nomor_anggota}/status")
def cek_status(nomor_anggota: str, db: Session = Depends(get_db)):
    """
    Cek status keanggotaan dan iuran
    """
    anggota = db.query(Anggota).filter(Anggota.nomor_anggota == nomor_anggota).first()
    if not anggota:
        raise HTTPException(404, "Anggota tidak ditemukan")
    
    user = db.query(User).filter(User.id == anggota.user_id).first()
    
    # Hitung tunggakan iuran wajib
    tunggakan = helpers.hitung_bulan_tunggakan(anggota.terakhir_bayar_wajib)
    
    # Hitung total token aktif
    token_aktif = db.query(Token).filter(
        Token.owner_id == anggota.user_id,
        Token.status == "active"
    ).count()
    
    harga = get_gold_price()
    
    return {
        "nomor_anggota": anggota.nomor_anggota,
        "nama": user.full_name if user else "Unknown",
        "status": anggota.status,
        "tanggal_daftar": anggota.created_at,
        "iuran_pokok": {
            "lunas": anggota.iuran_pokok_lunas,
            "rupiah": anggota.iuran_pokok_rupiah,
            "token": anggota.iuran_pokok_token,
            "formatted": helpers.format_rupiah(anggota.iuran_pokok_rupiah)
        },
        "iuran_wajib": {
            "terakhir_bayar": anggota.terakhir_bayar_wajib,
            "tunggakan_bulan": tunggakan,
            "tunggakan_rupiah": tunggakan * config.IURAN_WAJIB_RUPIAH,
            "tunggakan_token": tunggakan * config.IURAN_WAJIB_TOKEN,
            "formatted_tunggakan": helpers.format_rupiah(tunggakan * config.IURAN_WAJIB_RUPIAH)
        },
        "tabungan": {
            "total_setoran_rupiah": anggota.total_setoran_rupiah,
            "token_sukarela": anggota.simpanan_sukarela_token,
            "total_token_aktif": token_aktif,
            "setara_gram": token_aktif / config.TOKEN_PER_GRAM,
            "formatted_rupiah": helpers.format_rupiah(anggota.total_setoran_rupiah),
            "formatted_gram": helpers.format_gram(token_aktif / config.TOKEN_PER_GRAM)
        },
        "harga_emas": {
            "per_gram": harga["price_idr_per_gram"],
            "formatted": helpers.format_rupiah(harga["price_idr_per_gram"])
        }
    }

# ====================================================
# BAYAR IURAN WAJIB (Rp 500/bulan = 1 token)
# ====================================================
@router.post("/{nomor_anggota}/bayar-wajib")
def bayar_iuran_wajib(
    nomor_anggota: str,
    db: Session = Depends(get_db)
):
    """
    Membayar iuran wajib bulanan (Rp 500 = 1 token)
    """
    # Cari anggota
    anggota = db.query(Anggota).filter(
        Anggota.nomor_anggota == nomor_anggota
    ).first()
    
    if not anggota:
        raise HTTPException(404, "Anggota tidak ditemukan")
    
    # Cek apakah user punya cukup token
    token_user = db.query(Token).filter(
        Token.owner_id == anggota.user_id,
        Token.status == "active"
    ).count()
    
    if token_user < config.IURAN_WAJIB_TOKEN:
        raise HTTPException(
            400,
            f"Token tidak cukup. Butuh {config.IURAN_WAJIB_TOKEN} token, saldo {token_user}"
        )
    
    # Ambil token untuk pembayaran
    tokens_to_pay = db.query(Token).filter(
        Token.owner_id == anggota.user_id,
        Token.status == "active"
    ).limit(config.IURAN_WAJIB_TOKEN).all()
    
    for token in tokens_to_pay:
        token.status = "redeemed"
        token.owner_id = None
    
    # Update terakhir bayar
    anggota.terakhir_bayar_wajib = datetime.now()
    
    db.commit()
    
    # Catat ke blockchain
    blockchain.add_transaction({
        "type": "bayar_iuran_wajib",
        "nomor_anggota": nomor_anggota,
        "user_id": anggota.user_id,
        "jumlah_token": config.IURAN_WAJIB_TOKEN,
        "bulan": datetime.now().month,
        "tahun": datetime.now().year,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "message": f"Berhasil bayar iuran wajib Rp {config.IURAN_WAJIB_RUPIAH:,}",
        "data": {
            "nomor_anggota": anggota.nomor_anggota,
            "bulan": datetime.now().month,
            "tahun": datetime.now().year
        }
    }

# ====================================================
# GET SEMUA ANGGOTA (untuk admin)
# ====================================================
@router.get("/all")
def get_all_anggota(
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0
):
    """
    Mendapatkan daftar semua anggota (pagination)
    """
    total = db.query(Anggota).count()
    anggota_list = db.query(Anggota).offset(offset).limit(limit).all()
    
    result = []
    for a in anggota_list:
        user = db.query(User).filter(User.id == a.user_id).first()
        result.append({
            "id": a.id,
            "nomor_anggota": a.nomor_anggota,
            "nama": user.full_name if user else "Unknown",
            "status": a.status,
            "total_setoran": a.total_setoran_rupiah,
            "formatted_setoran": helpers.format_rupiah(a.total_setoran_rupiah),
            "created_at": a.created_at
        })
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": result
    }

# ====================================================
# GET ANGGOTA BY USER ID
# ====================================================
@router.get("/user/{user_id}")
def get_anggota_by_user_id(user_id: int, db: Session = Depends(get_db)):
    """
    Mendapatkan data anggota berdasarkan user_id
    """
    anggota = db.query(Anggota).filter(Anggota.user_id == user_id).first()
    if not anggota:
        raise HTTPException(404, "Anggota tidak ditemukan")
    
    user = db.query(User).filter(User.id == user_id).first()
    
    return {
        "user_id": user_id,
        "nomor_anggota": anggota.nomor_anggota,
        "nama": user.full_name if user else "Unknown",
        "status": anggota.status,
        "tanggal_daftar": anggota.created_at
    }

# ====================================================
# HITUNG TUNGGAKAN IURAN WAJIB
# ====================================================
@router.get("/{nomor_anggota}/tunggakan")
def hitung_tunggakan(nomor_anggota: str, db: Session = Depends(get_db)):
    """
    Hitung jumlah tunggakan iuran wajib
    """
    anggota = db.query(Anggota).filter(Anggota.nomor_anggota == nomor_anggota).first()
    if not anggota:
        raise HTTPException(404, "Anggota tidak ditemukan")
    
    tunggakan = helpers.hitung_bulan_tunggakan(anggota.terakhir_bayar_wajib)
    
    return {
        "nomor_anggota": nomor_anggota,
        "terakhir_bayar": anggota.terakhir_bayar_wajib,
        "tunggakan_bulan": tunggakan,
        "tunggakan_rupiah": tunggakan * config.IURAN_WAJIB_RUPIAH,
        "tunggakan_token": tunggakan * config.IURAN_WAJIB_TOKEN,
        "formatted_rupiah": helpers.format_rupiah(tunggakan * config.IURAN_WAJIB_RUPIAH)
    }