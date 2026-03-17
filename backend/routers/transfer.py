"""
Router untuk endpoint Transfer Token Antar Anggota
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from database import get_db, User, Anggota, Token
from utils import helpers
from blockchain import blockchain
import config

router = APIRouter(prefix="/transfer", tags=["Transfer"])

# ====================================================
# TRANSFER TOKEN ANTAR ANGGOTA
# ====================================================
@router.post("/")
def transfer_token(
    dari_user_id: int,
    ke_user_id: int,
    jumlah_token: int,
    catatan: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Transfer token antar anggota
    - Pengirim menanggung biaya admin 1%
    - Minimal transfer 1 token
    - Kedua user harus terdaftar
    """
    # Validasi dasar
    if jumlah_token < 1:
        raise HTTPException(400, "Minimal transfer 1 token")
    
    if dari_user_id == ke_user_id:
        raise HTTPException(400, "Tidak bisa transfer ke diri sendiri")
    
    # Cek pengirim
    pengirim = db.query(User).filter(User.id == dari_user_id).first()
    if not pengirim:
        raise HTTPException(404, "Pengirim tidak ditemukan")
    
    # Cek penerima
    penerima = db.query(User).filter(User.id == ke_user_id).first()
    if not penerima:
        raise HTTPException(404, "Penerima tidak ditemukan")
    
    # Cek apakah pengirim anggota aktif
    pengirim_anggota = db.query(Anggota).filter(
        Anggota.user_id == dari_user_id,
        Anggota.status == "aktif"
    ).first()
    
    if not pengirim_anggota:
        raise HTTPException(400, "Pengirim bukan anggota aktif")
    
    # Cek apakah penerima anggota aktif
    penerima_anggota = db.query(Anggota).filter(
        Anggota.user_id == ke_user_id,
        Anggota.status == "aktif"
    ).first()
    
    if not penerima_anggota:
        raise HTTPException(400, "Penerima bukan anggota aktif")
    
    # Hitung biaya admin
    biaya_admin_token = helpers.hitung_biaya_admin_token(jumlah_token)
    total_dikirim = jumlah_token + biaya_admin_token
    
    # Cek saldo pengirim
    saldo_pengirim = db.query(Token).filter(
        Token.owner_id == dari_user_id,
        Token.status == "active"
    ).count()
    
    if saldo_pengirim < total_dikirim:
        raise HTTPException(
            400, 
            f"Saldo tidak cukup. Butuh {total_dikirim} token, saldo {saldo_pengirim}"
        )
    
    # Ambil token pengirim
    tokens_pengirim = db.query(Token).filter(
        Token.owner_id == dari_user_id,
        Token.status == "active"
    ).limit(total_dikirim).all()
    
    # Bagi token:
    # - jumlah_token untuk penerima
    # - biaya_admin_token untuk koperasi
    token_penerima = tokens_pengirim[:jumlah_token]
    token_admin = tokens_pengirim[jumlah_token:]
    
    # Update kepemilikan
    for token in token_penerima:
        token.owner_id = ke_user_id
    
    for token in token_admin:
        token.owner_id = None
        token.status = "koperasi"
    
    db.commit()
    
    # Catat ke blockchain
    blockchain.add_transaction({
        "type": "transfer",
        "dari_user": dari_user_id,
        "ke_user": ke_user_id,
        "dari_nama": pengirim.full_name,
        "ke_nama": penerima.full_name,
        "jumlah_token": jumlah_token,
        "biaya_admin_token": biaya_admin_token,
        "total_dikirim": total_dikirim,
        "catatan": catatan,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "message": f"Transfer {jumlah_token} token berhasil",
        "data": {
            "dari": {
                "user_id": dari_user_id,
                "nama": pengirim.full_name
            },
            "ke": {
                "user_id": ke_user_id,
                "nama": penerima.full_name
            },
            "jumlah_token": jumlah_token,
            "biaya_admin_token": biaya_admin_token,
            "total_dikirim": total_dikirim,
            "catatan": catatan
        }
    }

# ====================================================
# TRANSFER VIA NOMOR ANGGOTA (ALTERNATIF)
# ====================================================
@router.post("/by-nomor")
def transfer_by_nomor(
    dari_nomor: str,
    ke_nomor: str,
    jumlah_token: int,
    catatan: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Transfer token menggunakan nomor anggota
    """
    # Cari pengirim berdasarkan nomor anggota
    pengirim_anggota = db.query(Anggota).filter(
        Anggota.nomor_anggota == dari_nomor,
        Anggota.status == "aktif"
    ).first()
    
    if not pengirim_anggota:
        raise HTTPException(404, f"Pengirim dengan nomor {dari_nomor} tidak ditemukan")
    
    # Cari penerima berdasarkan nomor anggota
    penerima_anggota = db.query(Anggota).filter(
        Anggota.nomor_anggota == ke_nomor,
        Anggota.status == "aktif"
    ).first()
    
    if not penerima_anggota:
        raise HTTPException(404, f"Penerima dengan nomor {ke_nomor} tidak ditemukan")
    
    # Panggil fungsi transfer dengan user_id
    return transfer_token(
        dari_user_id=pengirim_anggota.user_id,
        ke_user_id=penerima_anggota.user_id,
        jumlah_token=jumlah_token,
        catatan=catatan,
        db=db
    )

# ====================================================
# CEK BIAYA TRANSFER
# ====================================================
@router.get("/biaya")
def hitung_biaya_transfer(jumlah_token: int):
    """
    Menghitung biaya transfer untuk jumlah token tertentu
    """
    if jumlah_token < 1:
        raise HTTPException(400, "Jumlah token minimal 1")
    
    biaya = helpers.hitung_biaya_admin_token(jumlah_token)
    total = jumlah_token + biaya
    
    return {
        "jumlah_token": jumlah_token,
        "biaya_admin_token": biaya,
        "total_yang_harus_dikirim": total,
        "penerima_menerima": jumlah_token,
        "biaya_admin_persen": config.BIAYA_ADMIN_PERSEN * 100
    }

# ====================================================
# RIWAYAT TRANSFER USER
# ====================================================
@router.get("/riwayat/{user_id}")
def riwayat_transfer(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Mendapatkan riwayat transfer user (masuk/keluar)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    
    # Ambil dari blockchain, filter jenis transfer
    all_history = blockchain.get_transaction_history(user_id=user_id)
    transfer_history = [t for t in all_history if t.get("type") == "transfer"]
    
    # Urutkan terbaru
    transfer_history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Pagination
    paginated = transfer_history[offset:offset + limit]
    
    return {
        "user_id": user_id,
        "username": user.username,
        "total_transfer": len(transfer_history),
        "limit": limit,
        "offset": offset,
        "data": paginated
    }

# ====================================================
# CEK APAKAH BISA TRANSFER (VALIDASI)
# ====================================================
@router.get("/cek/{dari_user_id}/{ke_user_id}")
def cek_transfer(
    dari_user_id: int,
    ke_user_id: int,
    jumlah_token: int,
    db: Session = Depends(get_db)
):
    """
    Cek apakah transfer bisa dilakukan (tanpa eksekusi)
    """
    # Cek pengirim
    pengirim = db.query(User).filter(User.id == dari_user_id).first()
    if not pengirim:
        return {"bisa": False, "alasan": "Pengirim tidak ditemukan"}
    
    # Cek penerima
    penerima = db.query(User).filter(User.id == ke_user_id).first()
    if not penerima:
        return {"bisa": False, "alasan": "Penerima tidak ditemukan"}
    
    # Cek status anggota
    pengirim_anggota = db.query(Anggota).filter(
        Anggota.user_id == dari_user_id,
        Anggota.status == "aktif"
    ).first()
    
    if not pengirim_anggota:
        return {"bisa": False, "alasan": "Pengirim bukan anggota aktif"}
    
    penerima_anggota = db.query(Anggota).filter(
        Anggota.user_id == ke_user_id,
        Anggota.status == "aktif"
    ).first()
    
    if not penerima_anggota:
        return {"bisa": False, "alasan": "Penerima bukan anggota aktif"}
    
    # Cek saldo
    saldo = db.query(Token).filter(
        Token.owner_id == dari_user_id,
        Token.status == "active"
    ).count()
    
    biaya = helpers.hitung_biaya_admin_token(jumlah_token)
    total_dibutuhkan = jumlah_token + biaya
    
    if saldo < total_dibutuhkan:
        return {
            "bisa": False, 
            "alasan": f"Saldo tidak cukup. Butuh {total_dibutuhkan}, saldo {saldo}"
        }
    
    # Hitung biaya
    return {
        "bisa": True,
        "alasan": "Transfer dapat dilakukan",
        "detail": {
            "jumlah_token": jumlah_token,
            "biaya_admin_token": biaya,
            "total_dikirim": total_dibutuhkan,
            "penerima_terima": jumlah_token,
            "saldo_pengirim": saldo,
            "sisa_setelah_transfer": saldo - total_dibutuhkan
        }
    }