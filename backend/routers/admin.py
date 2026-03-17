"""
Router untuk endpoint Admin
Semua endpoint untuk manajemen koperasi
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import Optional

from database import get_db, User, Anggota, Token, StokToken, EmasFisik, TransaksiIuran, TransaksiToken
from utils import helpers
from utils.harga_emas import get_gold_price
from blockchain import blockchain
import config

router = APIRouter(prefix="/admin", tags=["Admin"])

# ====================================================
# DASHBOARD ADMIN
# ====================================================
@router.get("/dashboard")
def dashboard_admin(db: Session = Depends(get_db)):
    """
    Dashboard statistik untuk admin
    """
    # Statistik User
    total_user = db.query(User).count()
    user_aktif = db.query(User).filter(User.is_active == True).count()
    
    # Statistik Anggota
    total_anggota = db.query(Anggota).count()
    anggota_aktif = db.query(Anggota).filter(Anggota.status == "aktif").count()
    
    # Statistik Stok Token
    stok_token = db.query(StokToken).order_by(StokToken.created_at.desc()).first()
    stok = stok_token.jumlah if stok_token else 0
    
    # Statistik Emas
    total_emas = db.query(func.sum(EmasFisik.jumlah_gram)).scalar() or 0
    
    # Statistik Keuangan
    total_iuran = db.query(func.sum(TransaksiIuran.jumlah)).scalar() or 0
    total_transaksi_token = db.query(TransaksiToken).count()
    
    # Blockchain stats
    blockchain_stats = blockchain.get_stats()
    
    # Harga emas
    harga = get_gold_price()
    
    return {
        "statistik": {
            "user": {
                "total": total_user,
                "aktif": user_aktif
            },
            "anggota": {
                "total": total_anggota,
                "aktif": anggota_aktif
            },
            "stok_token": stok,
            "emas_fisik": {
                "total_gram": total_emas,
                "nilai_rupiah": total_emas * harga['price_idr_per_gram']
            },
            "keuangan": {
                "total_iuran": total_iuran,
                "total_transaksi_token": total_transaksi_token
            },
            "blockchain": blockchain_stats
        },
        "harga_emas": {
            "per_gram": harga['price_idr_per_gram'],
            "formatted": helpers.format_rupiah(harga['price_idr_per_gram'])
        },
        "timestamp": datetime.now().isoformat()
    }

# ====================================================
# DAFTAR SEMUA USER
# ====================================================
@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0
):
    """
    Mendapatkan daftar semua user (dengan pagination)
    """
    total = db.query(User).count()
    users = db.query(User).offset(offset).limit(limit).all()
    
    result = []
    for u in users:
        # Cek apakah user adalah anggota
        anggota = db.query(Anggota).filter(Anggota.user_id == u.id).first()
        
        result.append({
            "id": u.id,
            "user_id": u.user_id,
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "is_active": u.is_active,
            "is_admin": u.is_admin,
            "is_anggota": anggota is not None,
            "nomor_anggota": anggota.nomor_anggota if anggota else None,
            "created_at": u.created_at.isoformat() if u.created_at else None
        })
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": result
    }

# ====================================================
# DAFTAR SEMUA ANGGOTA
# ====================================================
@router.get("/anggota")
def get_all_anggota(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Mendapatkan daftar semua anggota (dengan filter status)
    """
    query = db.query(Anggota)
    if status:
        query = query.filter(Anggota.status == status)
    
    total = query.count()
    anggota_list = query.offset(offset).limit(limit).all()
    
    result = []
    for a in anggota_list:
        user = db.query(User).filter(User.id == a.user_id).first()
        
        result.append({
            "id": a.id,
            "user_id": a.user_id,
            "nomor_anggota": a.nomor_anggota,
            "nama": user.full_name if user else "Unknown",
            "email": user.email if user else "-",
            "status": a.status,
            "saldo_iuran": a.saldo_iuran,
            "token_sukarela": a.token_sukarela,
            "created_at": a.created_at.isoformat() if a.created_at else None
        })
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": result
    }

# ====================================================
# DAFTAR SEMUA TOKEN
# ====================================================
@router.get("/tokens")
def get_all_tokens(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Mendapatkan daftar semua token
    """
    query = db.query(Token)
    if status:
        query = query.filter(Token.status == status)
    
    total = query.count()
    tokens = query.offset(offset).limit(limit).all()
    
    result = []
    for t in tokens:
        pemilik = None
        if t.owner_id:
            user = db.query(User).filter(User.id == t.owner_id).first()
            if user:
                pemilik = {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name
                }
        
        result.append({
            "id": t.id,
            "token_code": t.token_code,
            "status": t.status,
            "pemilik": pemilik,
            "issued_at": t.issued_at.isoformat() if t.issued_at else None,
            "redeemed_at": t.redeemed_at.isoformat() if t.redeemed_at else None
        })
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": result
    }

# ====================================================
# CEK STOK TOKEN
# ====================================================
@router.get("/stok-token")
def get_stok_token(db: Session = Depends(get_db)):
    """
    Mendapatkan jumlah stok token saat ini
    """
    stok = db.query(StokToken).order_by(StokToken.created_at.desc()).first()
    return {
        "stok_token": stok.jumlah if stok else 0
    }

# ====================================================
# DAFTAR EMAS FISIK
# ====================================================
@router.get("/emas-fisik")
def get_all_emas(db: Session = Depends(get_db)):
    """
    Mendapatkan daftar semua emas fisik
    """
    emas_list = db.query(EmasFisik).order_by(EmasFisik.created_at.desc()).all()
    
    total_gram = sum(e.jumlah_gram for e in emas_list)
    harga = get_gold_price()
    
    result = []
    for e in emas_list:
        result.append({
            "id": e.id,
            "tanggal": e.created_at.isoformat() if e.created_at else None,
            "jumlah_gram": e.jumlah_gram,
            "sumber": e.sumber,
            "keterangan": e.keterangan,
            "harga_per_gram": e.harga_per_gram,
            "nilai_rupiah": e.jumlah_gram * (e.harga_per_gram or harga["price_idr_per_gram"]),
            "created_at": e.created_at.isoformat() if e.created_at else None
        })
    
    return {
        "total_gram": total_gram,
        "formatted_gram": f"{total_gram:.2f} gram",
        "nilai_total_rupiah": total_gram * harga["price_idr_per_gram"],
        "formatted_nilai": helpers.format_rupiah(total_gram * harga["price_idr_per_gram"]),
        "data": result
    }

# ====================================================
# TAMBAH EMAS FISIK
# ====================================================
@router.post("/emas-fisik/tambah")
def tambah_emas(
    jumlah_gram: float,
    sumber: str,
    keterangan: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Menambah emas fisik ke koperasi
    """
    if jumlah_gram <= 0:
        raise HTTPException(status_code=400, detail="Jumlah gram harus positif")
    
    sumber_valid = ["modal_awal", "laba", "tabungan_anggota", "investasi", "donasi", "lainnya"]
    if sumber not in sumber_valid:
        raise HTTPException(status_code=400, detail=f"Sumber harus salah satu dari {sumber_valid}")
    
    harga = get_gold_price()
    
    emas = EmasFisik(
        jumlah_gram=jumlah_gram,
        sumber=sumber,
        keterangan=keterangan,
        harga_per_gram=harga["price_idr_per_gram"]
    )
    
    db.add(emas)
    
    # Tambah stok token
    stok_baru = int(jumlah_gram * config.TOKEN_PER_GRAM)
    stok = db.query(StokToken).order_by(StokToken.created_at.desc()).first()
    if stok:
        stok.jumlah += stok_baru
    else:
        stok = StokToken(jumlah=stok_baru)
        db.add(stok)
    
    db.commit()
    db.refresh(emas)
    
    return {
        "status": "success",
        "message": f"Berhasil menambah {jumlah_gram} gram emas, stok token +{stok_baru}",
        "data": {
            "id": emas.id,
            "jumlah_gram": emas.jumlah_gram,
            "sumber": emas.sumber,
            "keterangan": emas.keterangan
        }
    }

# ====================================================
# INISIALISASI EMAS AWAL
# ====================================================
@router.post("/emas-fisik/init")
def inisialisasi_emas_awal(db: Session = Depends(get_db)):
    """
    Inisialisasi emas awal koperasi 1 gram
    """
    sudah_ada = db.query(EmasFisik).filter(EmasFisik.sumber == "modal_awal").first()
    if sudah_ada:
        raise HTTPException(status_code=400, detail="Emas awal sudah diinisialisasi")
    
    harga = get_gold_price()
    
    emas_awal = EmasFisik(
        jumlah_gram=config.MODAL_EMAS_AWAL_GRAM,
        sumber="modal_awal",
        keterangan="Modal awal koperasi",
        harga_per_gram=harga['price_idr_per_gram']
    )
    
    db.add(emas_awal)
    
    # Inisialisasi stok token
    stok_awal = StokToken(jumlah=config.STOK_TOKEN_AWAL)
    db.add(stok_awal)
    
    db.commit()
    db.refresh(emas_awal)
    
    return {
        "status": "success",
        "message": f"Berhasil inisialisasi emas awal {config.MODAL_EMAS_AWAL_GRAM} gram",
        "data": {
            "id": emas_awal.id,
            "jumlah_gram": config.MODAL_EMAS_AWAL_GRAM,
            "stok_token": config.STOK_TOKEN_AWAL,
            "nilai_rupiah": config.MODAL_EMAS_AWAL_GRAM * harga['price_idr_per_gram']
        }
    }

# ====================================================
# STATISTIK KEUANGAN
# ====================================================
@router.get("/keuangan")
def statistik_keuangan(db: Session = Depends(get_db)):
    """
    Statistik keuangan koperasi
    """
    # Total setoran dari anggota
    total_iuran = db.query(func.sum(TransaksiIuran.jumlah)).scalar() or 0
    
    # Total emas
    total_emas = db.query(func.sum(EmasFisik.jumlah_gram)).scalar() or 0
    
    # Total token
    total_token_beredar = db.query(Token).filter(Token.status == "active").count()
    stok_token = db.query(StokToken).order_by(StokToken.created_at.desc()).first()
    stok = stok_token.jumlah if stok_token else 0
    
    harga = get_gold_price()
    
    return {
        "pendapatan": {
            "total_iuran": total_iuran,
            "formatted_iuran": helpers.format_rupiah(total_iuran)
        },
        "aset": {
            "emas_gram": total_emas,
            "formatted_emas": f"{total_emas:.2f} gram",
            "nilai_emas": total_emas * harga["price_idr_per_gram"],
            "formatted_nilai_emas": helpers.format_rupiah(total_emas * harga["price_idr_per_gram"]),
            "stok_token": stok,
            "token_beredar": total_token_beredar
        }
    }

# ====================================================
# RIWAYAT TRANSAKSI IURAN
# ====================================================
@router.get("/transaksi-iuran")
def get_transaksi_iuran(
    anggota_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Mendapatkan riwayat transaksi iuran
    """
    query = db.query(TransaksiIuran).order_by(TransaksiIuran.created_at.desc())
    if anggota_id:
        query = query.filter(TransaksiIuran.anggota_id == anggota_id)
    
    transaksi = query.limit(limit).all()
    
    return [
        {
            "id": t.id,
            "anggota_id": t.anggota_id,
            "jenis": t.jenis,
            "jumlah": t.jumlah,
            "saldo_sebelum": t.saldo_sebelum,
            "saldo_sesudah": t.saldo_sesudah,
            "keterangan": t.keterangan,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        for t in transaksi
    ]

# ====================================================
# RIWAYAT TRANSAKSI TOKEN
# ====================================================
@router.get("/transaksi-token")
def get_transaksi_token(
    anggota_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Mendapatkan riwayat transaksi token
    """
    query = db.query(TransaksiToken).order_by(TransaksiToken.created_at.desc())
    if anggota_id:
        query = query.filter(TransaksiToken.anggota_id == anggota_id)
    
    transaksi = query.limit(limit).all()
    
    return [
        {
            "id": t.id,
            "anggota_id": t.anggota_id,
            "jenis": t.jenis,
            "jumlah_token": t.jumlah_token,
            "nilai_rupiah": t.nilai_rupiah,
            "biaya_admin": t.biaya_admin,
            "token_sebelum": t.token_sebelum,
            "token_sesudah": t.token_sesudah,
            "keterangan": t.keterangan,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        for t in transaksi
    ]

# ====================================================
# RESET DATABASE (HATI-HATI!)
# ====================================================
@router.post("/reset")
def reset_database(db: Session = Depends(get_db)):
    """
    RESET DATABASE - HAPUS SEMUA DATA!
    Hanya untuk development
    """
    # Hapus semua data
    db.query(Token).delete()
    db.query(TransaksiToken).delete()
    db.query(TransaksiIuran).delete()
    db.query(Anggota).delete()
    db.query(User).delete()
    db.query(EmasFisik).delete()
    db.query(StokToken).delete()
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Database telah direset"
    }