"""
Blockchain untuk Koperasi Token Emas
Mencatat semua transaksi sebagai bukti yang tidak bisa diubah
"""

import hashlib
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class Blockchain:
    def __init__(self, data_dir="data/blockchain"):
        self.data_dir = data_dir
        self.blocks_dir = os.path.join(data_dir, "blocks")
        self.chain_file = os.path.join(data_dir, "chain.json")
        self.pending_file = os.path.join(data_dir, "pending.json")
        
        # Buat folder jika belum ada
        os.makedirs(self.blocks_dir, exist_ok=True)
        
        # Load atau buat blockchain baru
        self.chain = self.load_chain()
        self.pending_transactions = self.load_pending()
        
        # Jika chain kosong, buat genesis block
        if len(self.chain) == 0:
            self.create_genesis_block()
    
    def load_chain(self) -> List[Dict]:
        """Load metadata chain dari file"""
        if os.path.exists(self.chain_file):
            with open(self.chain_file, 'r') as f:
                return json.load(f)
        return []
    
    def load_pending(self) -> List[Dict]:
        """Load pending transactions"""
        if os.path.exists(self.pending_file):
            with open(self.pending_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_chain_metadata(self):
        """Simpan metadata chain (hanya index dan hash)"""
        metadata = [{"index": b["index"], "hash": b["hash"]} for b in self.chain]
        with open(self.chain_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def save_pending(self):
        """Simpan pending transactions"""
        with open(self.pending_file, 'w') as f:
            json.dump(self.pending_transactions, f, indent=2)
    
    def save_block(self, block: Dict):
        """Simpan satu block ke file terpisah"""
        block_file = os.path.join(self.blocks_dir, f"block_{block['index']}.json")
        with open(block_file, 'w') as f:
            json.dump(block, f, indent=2)
    
    def load_block(self, index: int) -> Optional[Dict]:
        """Load satu block dari file"""
        block_file = os.path.join(self.blocks_dir, f"block_{index}.json")
        if os.path.exists(block_file):
            with open(block_file, 'r') as f:
                return json.load(f)
        return None
    
    def calculate_hash(self, block: Dict) -> str:
        """Hitung hash SHA-256 dari block"""
        block_string = json.dumps({
            "index": block["index"],
            "timestamp": block["timestamp"],
            "transactions": block["transactions"],
            "previous_hash": block["previous_hash"],
            "nonce": block.get("nonce", 0)
        }, sort_keys=True)
        
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def create_genesis_block(self):
        """Buat block pertama (genesis)"""
        genesis = {
            "index": 0,
            "timestamp": str(datetime.now()),
            "transactions": [{
                "type": "genesis",
                "data": "Koperasi Token Emas didirikan",
                "timestamp": str(datetime.now())
            }],
            "previous_hash": "0" * 64,
            "nonce": 0
        }
        
        # Hitung hash genesis
        genesis["hash"] = self.calculate_hash(genesis)
        
        # Simpan block genesis
        self.save_block(genesis)
        
        # Tambahkan ke chain metadata
        self.chain.append({"index": genesis["index"], "hash": genesis["hash"]})
        self.save_chain_metadata()
        
        print("✅ Genesis block created")
        return genesis
    
    def add_transaction(self, transaction: Dict):
        """Tambahkan transaksi ke pending"""
        self.pending_transactions.append({
            **transaction,
            "timestamp": str(datetime.now()),
            "status": "pending"
        })
        self.save_pending()
        print(f"✅ Transaksi ditambahkan ke pending. Total: {len(self.pending_transactions)}")
    
    def mine_block(self) -> Optional[Dict]:
        """Tambang block baru (pindahkan pending ke chain)"""
        if not self.pending_transactions:
            print("⚠️ Tidak ada transaksi pending")
            return None
        
        # Ambil block terakhir
        previous_block_meta = self.chain[-1]
        previous_block = self.load_block(previous_block_meta["index"])
        
        if not previous_block:
            print("❌ Gagal load block sebelumnya")
            return None
        
        # Buat block baru
        new_block = {
            "index": len(self.chain),
            "timestamp": str(datetime.now()),
            "transactions": self.pending_transactions.copy(),
            "previous_hash": previous_block["hash"],
            "nonce": 0
        }
        
        # Simple proof of work (bisa disesuaikan)
        difficulty = 2
        prefix = "0" * difficulty
        
        print(f"⛏️  Mining block #{new_block['index']}...")
        
        while True:
            new_block["hash"] = self.calculate_hash(new_block)
            if new_block["hash"].startswith(prefix):
                break
            new_block["nonce"] += 1
        
        # Simpan block
        self.save_block(new_block)
        
        # Update chain metadata
        self.chain.append({"index": new_block["index"], "hash": new_block["hash"]})
        
        # Kosongkan pending
        self.pending_transactions = []
        
        # Simpan semua
        self.save_chain_metadata()
        self.save_pending()
        
        print(f"✅ Block #{new_block['index']} berhasil ditambang")
        print(f"   Hash: {new_block['hash'][:20]}...")
        print(f"   Transaksi: {len(new_block['transactions'])}")
        
        return new_block
    
    def is_chain_valid(self) -> bool:
        """Verifikasi seluruh blockchain"""
        print("🔍 Verifikasi blockchain...")
        
        for i in range(1, len(self.chain)):
            current_meta = self.chain[i]
            previous_meta = self.chain[i-1]
            
            # Load block dari file
            current = self.load_block(current_meta["index"])
            previous = self.load_block(previous_meta["index"])
            
            if not current or not previous:
                print(f"❌ Block {i} atau {i-1} tidak ditemukan")
                return False
            
            # Cek hash block
            if current["hash"] != self.calculate_hash(current):
                print(f"❌ Hash block {i} tidak valid")
                return False
            
            # Cek hubungan dengan previous block
            if current["previous_hash"] != previous["hash"]:
                print(f"❌ Previous hash block {i} tidak cocok")
                return False
        
        print("✅ Blockchain valid!")
        return True
    
    def get_transaction_history(self, user_id: int = None, nomor_anggota: str = None) -> List[Dict]:
        """Ambil riwayat transaksi berdasarkan filter"""
        history = []
        
        for meta in self.chain:
            block = self.load_block(meta["index"])
            if not block:
                continue
                
            for tx in block["transactions"]:
                if tx.get("type") == "genesis":
                    continue
                
                # Filter berdasarkan kriteria
                match = False
                if user_id is not None:
                    if tx.get("user_id") == user_id or tx.get("anggota_id") == user_id:
                        match = True
                if nomor_anggota is not None:
                    if tx.get("nomor_anggota") == nomor_anggota:
                        match = True
                
                # Jika tidak ada filter, ambil semua
                if user_id is None and nomor_anggota is None:
                    match = True
                
                if match:
                    history.append({
                        **tx,
                        "block_index": block["index"],
                        "block_hash": block["hash"]
                    })
        
        return history
    
    def get_stats(self) -> Dict:
        """Dapatkan statistik blockchain"""
        total_blocks = len(self.chain)
        total_transactions = 0
        for meta in self.chain:
            block = self.load_block(meta["index"])
            if block:
                total_transactions += len(block["transactions"])
        
        return {
            "total_blocks": total_blocks,
            "total_transactions": total_transactions,
            "pending_transactions": len(self.pending_transactions),
            "last_block_hash": self.chain[-1]["hash"] if self.chain else None,
            "last_block_index": self.chain[-1]["index"] if self.chain else None
        }

# Buat instance global (singleton)
blockchain = Blockchain()

# Untuk testing kalau dijalankan langsung
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING BLOCKCHAIN")
    print("=" * 50)
    
    bc = Blockchain()
    
    # Tambah beberapa transaksi dummy
    bc.add_transaction({
        "type": "transfer",
        "dari_user": 1,
        "ke_user": 2,
        "jumlah_token": 100,
        "biaya_admin": 0
    })
    
    bc.add_transaction({
        "type": "beli_token",
        "user_id": 3,
        "jumlah_token": 50,
        "biaya_admin": 1
    })
    
    # Mine block
    bc.mine_block()
    
    # Tambah lagi
    bc.add_transaction({
        "type": "jual_token",
        "user_id": 1,
        "jumlah_token": 20
    })
    
    bc.mine_block()
    
    # Verifikasi
    bc.is_chain_valid()
    
    # Lihat statistik
    print("\n📊 Statistik:")
    stats = bc.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")