#!/usr/bin/env python3
import requests
import sys

API_URL = "http://localhost:8000"

def test_endpoint(name, url):
    print(f"\n🔍 Testing {name}: {url}")
    try:
        response = requests.get(url, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Sukses! Data: {str(data)[:100]}...")
            return True
        else:
            print(f"   ❌ Gagal: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Gagal: Tidak dapat terhubung ke server")
        return False
    except Exception as e:
        print(f"   ❌ Gagal: {e}")
        return False

def main():
    print("=" * 50)
    print("TEST KONEKSI KE BACKEND")
    print("=" * 50)
    
    # Test root
    test_endpoint("Root", f"{API_URL}/")
    
    # Test info
    test_endpoint("Info", f"{API_URL}/info")
    
    # Test harga
    test_endpoint("Harga", f"{API_URL}/harga")
    
    # Test admin users
    test_endpoint("Admin Users", f"{API_URL}/admin/users")

if __name__ == "__main__":
    main()