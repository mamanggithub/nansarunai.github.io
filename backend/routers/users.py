"""
Router untuk endpoint User
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from database import get_db, User, Token
from utils import helpers
from utils.harga_emas import get_gold_price
from blockchain import blockchain

router = APIRouter(prefix="/users", tags=["Users"])

# ====================================================
# REGISTRASI USER BARU
# ====================================================
@router.post("/register")
def register_user(
    username: str,
    email: str,
    full_name: str,
    db: Session = Depends(get_db)
):
    """
    Registrasi user baru (belum jadi anggota)
    """
    # Validasi input
    if not helpers.validasi_username(username):
        raise HTTPException(400, "Username tidak valid (min 3 karakter, huruf/angka/_ )")
    
    if not helpers.validasi_email(email):
        raise HTTPException(400, "Email tidak valid")
    
    # Cek duplikat
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "Username sudah digunakan")
    
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email sudah terdaftar")
    
    # Buat user baru
    user = User(
        user_id=helpers.generate_user_id(),
        username=username,
        email=email,
        full_name=full_name,
        hashed_password="",  # Nanti diisi kalau pakai login
        is_active=True,
        is_admin=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Catat ke blockchain
    blockchain.add_transaction({
        "type": "user_registration",
        "user_id": user.id,
        "username": username,
        "email": email,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "message": "Registrasi berhasil",
        "data": {
            "id": user.id,
            "user_id": user.user_id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email
        }
    }

# ====================================================
# CEK SALDO USER
# ====================================================
@router.get("/{user_id}/saldo")
def cek_saldo(user_id: int, db: Session = Depends(get_db)):
    """
    Cek saldo token user
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    # Hitung token aktif
    token_aktif = db.query(Token).filter(
        Token.owner_id == user_id,
        Token.status == "active"
    ).count()
    
    # Cek apakah anggota
    from database import Anggota
    anggota = db.query(Anggota).filter(Anggota.user_id == user_id).first()
    
    harga = get_gold_price()
    
    return {
        "user_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "status_anggota": anggota.status if anggota else "non_anggota",
        "nomor_anggota": anggota.nomor_anggota if anggota else None,
        "saldo": {
            "token": token_aktif,
            "rupiah": token_aktif * 500,
            "gram_emas": token_aktif / 2000,
            "formatted_rupiah": helpers.format_rupiah(token_aktif * 500),
            "formatted_gram": helpers.format_gram(token_aktif / 2000)
        },
        "harga_emas": {
            "per_gram": harga["price_idr_per_gram"],
            "formatted": helpers.format_rupiah(harga["price_idr_per_gram"])
        }
    }

# ====================================================
# GET PROFILE USER
# ====================================================
@router.get("/{user_id}")
def get_profile(user_id: int, db: Session = Depends(get_db)):
    """
    Mendapatkan profil user
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    return {
        "id": user.id,
        "user_id": user.user_id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "created_at": user.created_at
    }

# ====================================================
# UPDATE PROFILE USER
# ====================================================
@router.put("/{user_id}")
def update_profile(
    user_id: int,
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Update profil user
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    if full_name:
        user.full_name = full_name
    
    if email:
        if not helpers.validasi_email(email):
            raise HTTPException(400, "Email tidak valid")
        
        # Cek duplikat email
        existing = db.query(User).filter(User.email == email, User.id != user_id).first()
        if existing:
            raise HTTPException(400, "Email sudah digunakan user lain")
        
        user.email = email
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": "Profil berhasil diupdate",
        "data": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email
        }
    }

# ====================================================
# NONAKTIFKAN USER
# ====================================================
@router.delete("/{user_id}")
def deactivate_user(user_id: int, db: Session = Depends(get_db)):
    """
    Nonaktifkan user (soft delete)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    user.is_active = False
    db.commit()
    
    # Catat ke blockchain
    blockchain.add_transaction({
        "type": "user_deactivated",
        "user_id": user_id,
        "username": user.username,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "message": "User dinonaktifkan"
    }

# ====================================================
# CEK STATUS KEAKTIFAN
# ====================================================
@router.get("/{user_id}/status")
def check_status(user_id: int, db: Session = Depends(get_db)):
    """
    Cek status keaktifan user
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    return {
        "user_id": user.id,
        "username": user.username,
        "is_active": user.is_active,
        "is_admin": user.is_admin
    }