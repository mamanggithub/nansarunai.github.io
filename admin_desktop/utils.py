"""
Fungsi bantuan untuk Admin Desktop
"""

import requests
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

def format_rupiah(angka):
    """Format angka ke rupiah"""
    return f"Rp {angka:,.0f}".replace(',', '.')

def format_token(jumlah):
    """Format jumlah token"""
    return f"{jumlah:,} token".replace(',', '.')

def format_gram(gram):
    """Format gram emas"""
    return f"{gram:.2f} gram"

def api_get(endpoint):
    """GET request ke API"""
    try:
        response = requests.get(f"{API_URL}{endpoint}", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"error": "Tidak dapat terhubung ke server"}
    except Exception as e:
        return {"error": str(e)}

def api_post(endpoint, data=None):
    """POST request ke API"""
    try:
        if data:
            response = requests.post(f"{API_URL}{endpoint}", json=data, timeout=5)
        else:
            response = requests.post(f"{API_URL}{endpoint}", timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"error": "Tidak dapat terhubung ke server"}
    except Exception as e:
        return {"error": str(e)}

def center_window(window, width, height):
    """Center window di layar"""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f'{width}x{height}+{x}+{y}')

def create_tooltip(widget, text):
    """Buat tooltip untuk widget"""
    def enter(event):
        x, y, _, _ = widget.bbox("insert")
        x += widget.winfo_rootx() + 25
        y += widget.winfo_rooty() + 25
        
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(
            tooltip,
            text=text,
            bg='#1a1e24',
            fg='#e5e7eb',
            font=('Inter', 9),
            padx=10,
            pady=5,
            relief='solid',
            borderwidth=1
        )
        label.pack()
        
        widget.tooltip = tooltip
    
    def leave(event):
        if hasattr(widget, 'tooltip'):
            widget.tooltip.destroy()
    
    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)