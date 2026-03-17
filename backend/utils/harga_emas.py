"""
Modul untuk mengambil harga emas dan kurs dari API eksternal
"""

import requests
import random
import time
from datetime import datetime, timedelta

# Cache untuk menyimpan harga agar tidak terlalu sering request
cache = {
    "harga": None,
    "kurs": None,
    "timestamp": 0
}

# Konfigurasi
CACHE_DURATION = 300  # 5 menit (300 detik)
API_GOLD = "https://api.gold-api.com/price/XAU"
API_KURS = "https://open.er-api.com/v6/latest/USD"

def get_gold_price(force_refresh=False):
    """
    Mengambil harga emas terkini dari API eksternal
    
    Returns:
        dict: {
            "price_usd": float,        # Harga per troy ons dalam USD
            "price_idr_per_gram": float, # Harga per gram dalam IDR
            "usd_to_idr": float,        # Kurs USD ke IDR
            "nilai_per_token": float,    # Nilai 1 token dalam rupiah
            "timestamp": str,            # Waktu update
            "source": str                # Sumber data (cache/api)
        }
    """
    global cache
    
    now = time.time()
    
    # Gunakan cache jika masih valid dan tidak dipaksa refresh
    if not force_refresh and (now - cache["timestamp"]) < CACHE_DURATION:
        if cache["harga"] is not None and cache["kurs"] is not None:
            return _format_response(cache["harga"], cache["kurs"], "cache")
    
    # Ambil data dari API
    try:
        # Ambil harga emas
        gold_response = requests.get(API_GOLD, timeout=10)
        gold_response.raise_for_status()
        gold_data = gold_response.json()
        price_usd = gold_data.get("price", 0)
        
        # Ambil kurs USD/IDR
        kurs_response = requests.get(API_KURS, timeout=10)
        kurs_response.raise_for_status()
        kurs_data = kurs_response.json()
        usd_to_idr = kurs_data["rates"].get("IDR", 0)
        
        # Update cache
        cache["harga"] = price_usd
        cache["kurs"] = usd_to_idr
        cache["timestamp"] = now
        
        return _format_response(price_usd, usd_to_idr, "api")
        
    except requests.exceptions.RequestException as e:
        print(f"Error mengambil data dari API: {e}")
        
        # Jika ada cache, gunakan cache meskipun sudah expired
        if cache["harga"] is not None and cache["kurs"] is not None:
            print("Menggunakan data cache (expired)")
            return _format_response(cache["harga"], cache["kurs"], "cache (expired)")
        
        # Jika tidak ada cache, gunakan data dummy
        print("Menggunakan data dummy")
        return _format_response(2000, 15500, "dummy")

def _format_response(price_usd, usd_to_idr, source):
    """
    Format response harga emas
    """
    # 1 troy ons = 31.1034768 gram
    price_per_gram_usd = price_usd / 31.1034768
    price_per_gram_idr = price_per_gram_usd * usd_to_idr
    
    # 1 gram = 2000 token
    nilai_per_token = price_per_gram_idr / 2000
    
    return {
        "price_usd": round(price_usd, 2),
        "price_idr_per_gram": round(price_per_gram_idr, 2),
        "usd_to_idr": round(usd_to_idr, 2),
        "nilai_per_token": round(nilai_per_token, 2),
        "timestamp": datetime.now().isoformat(),
        "source": source
    }

def get_historical_prices(days=7):
    """
    Ambil data historis harga emas (simulasi dengan variasi kecil)
    Berdasarkan harga terkini dengan variasi ±2%
    """
    base_price = get_gold_price()["price_idr_per_gram"]
    historical = []
    
    for i in range(days, 0, -1):
        date = datetime.now() - timedelta(days=i)
        # Variasi kecil (±2%) untuk simulasi data historis
        variation = 1 + (random.random() * 0.04 - 0.02)
        price = base_price * variation
        
        historical.append({
            "date": date.strftime("%Y-%m-%d"),
            "price": round(price, 2)
        })
    
    return historical

def get_kurs_historical(days=7):
    """
    Ambil data historis kurs USD/IDR
    Berdasarkan kurs terkini dengan variasi ±1%
    """
    base_kurs = get_gold_price()["usd_to_idr"]
    historical = []
    
    for i in range(days, 0, -1):
        date = datetime.now() - timedelta(days=i)
        variation = 1 + (random.random() * 0.02 - 0.01)  # Variasi ±1%
        kurs = base_kurs * variation
        
        historical.append({
            "date": date.strftime("%Y-%m-%d"),
            "kurs": round(kurs, 2)
        })
    
    return historical

# Untuk testing
if __name__ == "__main__":
    print("=" * 50)
    print("TESTING FUNGSI HARGA EMAS")
    print("=" * 50)
    
    harga = get_gold_price(force_refresh=True)
    print(f"Harga emas: Rp {harga['price_idr_per_gram']:,.0f}/gram")
    print(f"Nilai 1 token: Rp {harga['nilai_per_token']}")
    print(f"Kurs USD/IDR: Rp {harga['usd_to_idr']}")
    
    print("\nData historis 7 hari:")
    historis = get_historical_prices(7)
    for h in historis[:3]:
        print(f"  {h['date']}: Rp {h['price']:,.0f}")
    print("  ...")