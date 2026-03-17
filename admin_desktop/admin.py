#!/usr/bin/env python3
"""
Admin Desktop - Koperasi Token Emas
Aplikasi desktop untuk manajemen koperasi
Versi dengan perhitungan laba & aset yang benar
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime
import requests

# ====================================================
# KONFIGURASI
# ====================================================
API_URL = "http://localhost:8000"

COLORS = {
    'bg_dark': '#0a0c0f',
    'bg_card': '#1a1e24',
    'bg_input': '#0f1319',
    'fg_text': '#e5e7eb',
    'fg_muted': '#9ca3af',
    'accent': '#ffd700',
    'accent_hover': '#e6c200',
    'success': '#4ade80',
    'warning': '#fbbf24',
    'error': '#ef4444',
    'border': '#2a3038'
}

FONTS = {
    'title': ('Playfair Display', 20, 'bold'),
    'heading': ('Inter', 14, 'bold'),
    'normal': ('Inter', 10),
    'small': ('Inter', 9)
}

REFRESH_INTERVAL = 30

# ====================================================
# FUNGSI BANTUAN
# ====================================================

def format_rupiah(angka):
    """Format angka ke rupiah"""
    try:
        return f"Rp {angka:,.0f}".replace(',', '.')
    except:
        return "Rp 0"

def api_get(endpoint):
    """GET request ke API dengan error handling"""
    full_url = f"{API_URL}{endpoint}"
    print(f"GET: {full_url}")
    
    try:
        response = requests.get(full_url, timeout=5)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"error": "Tidak dapat terhubung ke server"}
    except Exception as e:
        return {"error": str(e)}

def api_post(endpoint, params=None):
    """POST request ke API"""
    full_url = f"{API_URL}{endpoint}"
    print(f"POST: {full_url}")
    
    try:
        if params:
            response = requests.post(full_url, params=params, timeout=5)
        else:
            response = requests.post(full_url, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def center_window(window, width, height):
    """Center window di layar"""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f'{width}x{height}+{x}+{y}')

# ====================================================
# KELAS UTAMA
# ====================================================

class AdminDesktop:
    def __init__(self, root):
        self.root = root
        self.root.title("Admin Desktop - Koperasi Token Emas")
        self.root.geometry("1200x700")
        self.root.configure(bg=COLORS['bg_dark'])
        
        center_window(self.root, 1200, 700)
        
        self.auto_refresh = True
        self.refresh_thread = None
        
        self.setup_ui()
        self.after_load()
        self.start_auto_refresh()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Setup semua komponen UI"""
        
        self.main_container = tk.Frame(self.root, bg=COLORS['bg_dark'])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.create_header()
        
        # Notebook
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Style untuk notebook
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background=COLORS['bg_dark'], borderwidth=0)
        style.configure('TNotebook.Tab', 
                       background=COLORS['bg_card'],
                       foreground=COLORS['fg_text'],
                       padding=[15, 5],
                       font=('Inter', 10))
        style.map('TNotebook.Tab',
                 background=[('selected', COLORS['accent']), ('active', COLORS['bg_input'])],
                 foreground=[('selected', COLORS['bg_dark']), ('active', COLORS['fg_text'])])
        
        self.create_dashboard_tab()
        self.create_users_tab()
        self.create_anggota_tab()
        self.create_token_tab()
        self.create_emas_tab()
        self.create_settings_tab()
        
        self.create_status_bar()
    
    def create_header(self):
        """Buat header"""
        header = tk.Frame(self.main_container, bg=COLORS['bg_dark'])
        header.pack(fill=tk.X, pady=(0, 10))
        
        logo_frame = tk.Frame(header, bg=COLORS['bg_dark'])
        logo_frame.pack(side=tk.LEFT)
        
        logo_icon = tk.Label(
            logo_frame,
            text="🏦",
            font=('Arial', 32),
            bg=COLORS['bg_dark'],
            fg=COLORS['accent']
        )
        logo_icon.pack(side=tk.LEFT, padx=(0, 10))
        
        logo_text = tk.Label(
            logo_frame,
            text="Koperasi Token Emas",
            font=FONTS['title'],
            bg=COLORS['bg_dark'],
            fg=COLORS['accent']
        )
        logo_text.pack(side=tk.LEFT)
        
        self.status_server = tk.Label(
            header,
            text="⏳ Menghubungkan...",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['fg_muted'],
            padx=15,
            pady=5
        )
        self.status_server.pack(side=tk.RIGHT)
        
        self.check_server()
    
    def create_status_bar(self):
        """Buat status bar"""
        status_bar = tk.Frame(self.main_container, bg=COLORS['bg_dark'])
        status_bar.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Separator(status_bar, orient='horizontal').pack(fill=tk.X, pady=(0, 5))
        
        self.status_text = tk.Label(
            status_bar,
            text="✅ Sistem siap",
            font=FONTS['small'],
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_muted']
        )
        self.status_text.pack(side=tk.LEFT)
        
        self.last_update = tk.Label(
            status_bar,
            text="",
            font=FONTS['small'],
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_muted']
        )
        self.last_update.pack(side=tk.RIGHT)
    
    def create_dashboard_tab(self):
        """Buat tab Dashboard dengan Neraca Laba & Aset Emas"""
        tab = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        self.notebook.add(tab, text="📊 Dashboard")
        
        # ====================================================
        # ROW 1: STATISTIK UTAMA (4 CARD)
        # ====================================================
        cards_frame = tk.Frame(tab, bg=COLORS['bg_dark'])
        cards_frame.pack(fill=tk.X, pady=10)
        
        for i in range(4):
            cards_frame.columnconfigure(i, weight=1)
        
        self.stats = {}
        stats_data = [
            ("👥 Anggota Aktif", "0", "orang"),
            ("🪙 Stok Token", "0", "token"),
            ("💰 Total Kas", "Rp 0", ""),
            ("📈 Harga Emas", "Rp 0", "/gram")
        ]
        
        for i, (title, value, unit) in enumerate(stats_data):
            card = self.create_stat_card(cards_frame, title, value, unit)
            card.grid(row=0, column=i, padx=5, sticky='ew')
            self.stats[title] = card
        
        # ====================================================
        # ROW 2: NERACA LABA (2 KOTAK BESAR)
        # ====================================================
        laba_frame = tk.Frame(tab, bg=COLORS['bg_dark'])
        laba_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        laba_frame.grid_columnconfigure(0, weight=1)
        laba_frame.grid_columnconfigure(1, weight=1)
        laba_frame.grid_rowconfigure(0, weight=1)
        
        # ====================================================
        # KOTAK 1: LABA DARI PENJUALAN TOKEN
        # ====================================================
        laba_token_frame = tk.Frame(laba_frame, bg=COLORS['bg_card'], relief=tk.RAISED, bd=2)
        laba_token_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        
        tk.Label(
            laba_token_frame,
            text="💰 LABA PENJUALAN TOKEN",
            font=FONTS['heading'],
            bg=COLORS['bg_card'],
            fg=COLORS['accent'],
            pady=15
        ).pack()
        
        # Detail laba token
        token_detail_frame = tk.Frame(laba_token_frame, bg=COLORS['bg_card'])
        token_detail_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Rumus: Nilai per token + admin 1% dari nilai pembelian
        rumus_frame = tk.Frame(token_detail_frame, bg=COLORS['bg_card'])
        rumus_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            rumus_frame,
            text="📐 Rumus: Nilai token + 1% admin",
            font=FONTS['small'],
            bg=COLORS['bg_card'],
            fg=COLORS['fg_muted']
        ).pack()
        
        # Beli Token (biaya admin)
        beli_frame = tk.Frame(token_detail_frame, bg=COLORS['bg_card'])
        beli_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            beli_frame,
            text="💳 Admin Pembelian Token:",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['fg_text'],
            anchor='w'
        ).pack(side=tk.LEFT)
        
        self.laba_beli_token = tk.Label(
            beli_frame,
            text="Rp 0",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['success'],
            anchor='e'
        )
        self.laba_beli_token.pack(side=tk.RIGHT)
        
        # Jual Token (biaya admin)
        jual_frame = tk.Frame(token_detail_frame, bg=COLORS['bg_card'])
        jual_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            jual_frame,
            text="💸 Admin Penjualan Token:",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['fg_text'],
            anchor='w'
        ).pack(side=tk.LEFT)
        
        self.laba_jual_token = tk.Label(
            jual_frame,
            text="Rp 0",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['success'],
            anchor='e'
        )
        self.laba_jual_token.pack(side=tk.RIGHT)
        
        # Separator
        ttk.Separator(token_detail_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Total Laba Token
        total_token_frame = tk.Frame(token_detail_frame, bg=COLORS['bg_card'])
        total_token_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            total_token_frame,
            text="📊 TOTAL LABA TOKEN:",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['accent'],
            anchor='w'
        ).pack(side=tk.LEFT)
        
        self.total_laba_token = tk.Label(
            total_token_frame,
            text="Rp 0",
            font=('Playfair Display', 16, 'bold'),
            bg=COLORS['bg_card'],
            fg=COLORS['accent'],
            anchor='e'
        )
        self.total_laba_token.pack(side=tk.RIGHT)
        
        # ====================================================
        # KOTAK 2: ASET EMAS
        # ====================================================
        aset_emas_frame = tk.Frame(laba_frame, bg=COLORS['bg_card'], relief=tk.RAISED, bd=2)
        aset_emas_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
        
        tk.Label(
            aset_emas_frame,
            text="🏆 ASET EMAS KOPERASI",
            font=FONTS['heading'],
            bg=COLORS['bg_card'],
            fg=COLORS['accent'],
            pady=15
        ).pack()
        
        # Detail aset emas
        aset_detail_frame = tk.Frame(aset_emas_frame, bg=COLORS['bg_card'])
        aset_detail_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Rumus: Total sisa token × harga emas update
        rumus_aset_frame = tk.Frame(aset_detail_frame, bg=COLORS['bg_card'])
        rumus_aset_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            rumus_aset_frame,
            text="📐 Rumus: Stok Token × Harga Emas",
            font=FONTS['small'],
            bg=COLORS['bg_card'],
            fg=COLORS['fg_muted']
        ).pack()
        
        # Stok Token
        stok_frame = tk.Frame(aset_detail_frame, bg=COLORS['bg_card'])
        stok_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            stok_frame,
            text="🪙 Stok Token:",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['fg_text'],
            anchor='w'
        ).pack(side=tk.LEFT)
        
        self.stok_token_aset = tk.Label(
            stok_frame,
            text="0 token",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['fg_text'],
            anchor='e'
        )
        self.stok_token_aset.pack(side=tk.RIGHT)
        
        # Harga Emas
        harga_frame = tk.Frame(aset_detail_frame, bg=COLORS['bg_card'])
        harga_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            harga_frame,
            text="📈 Harga Emas/Gram:",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['fg_text'],
            anchor='w'
        ).pack(side=tk.LEFT)
        
        self.harga_emas_aset = tk.Label(
            harga_frame,
            text="Rp 0",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['success'],
            anchor='e'
        )
        self.harga_emas_aset.pack(side=tk.RIGHT)
        
        # Separator
        ttk.Separator(aset_detail_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Total Nilai Aset Emas
        total_aset_frame = tk.Frame(aset_detail_frame, bg=COLORS['bg_card'])
        total_aset_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            total_aset_frame,
            text="💰 NILAI ASET EMAS:",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['accent'],
            anchor='w'
        ).pack(side=tk.LEFT)
        
        self.total_aset_emas = tk.Label(
            total_aset_frame,
            text="Rp 0",
            font=('Playfair Display', 18, 'bold'),
            bg=COLORS['bg_card'],
            fg=COLORS['accent'],
            anchor='e'
        )
        self.total_aset_emas.pack(side=tk.RIGHT)
        
        # ====================================================
        # ROW 3: TOTAL SELURUH LABA
        # ====================================================
        total_all_frame = tk.Frame(tab, bg=COLORS['bg_dark'])
        total_all_frame.pack(fill=tk.X, pady=10)
        
        total_all_card = tk.Frame(total_all_frame, bg=COLORS['bg_card'], relief=tk.RAISED, bd=2)
        total_all_card.pack(fill=tk.X, padx=10)
        
        tk.Label(
            total_all_card,
            text="💎 TOTAL SELURUH LABA KOPERASI",
            font=FONTS['heading'],
            bg=COLORS['bg_card'],
            fg=COLORS['accent'],
            pady=10
        ).pack()
        
        total_laba_frame = tk.Frame(total_all_card, bg=COLORS['bg_card'])
        total_laba_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(
            total_laba_frame,
            text="💰 Laba Bersih (dari admin):",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['fg_text']
        ).pack(side=tk.LEFT)
        
        self.total_laba_all = tk.Label(
            total_laba_frame,
            text="Rp 0",
            font=('Playfair Display', 20, 'bold'),
            bg=COLORS['bg_card'],
            fg=COLORS['success']
        )
        self.total_laba_all.pack(side=tk.RIGHT)
        
        # Info tambahan
        info_frame = tk.Frame(tab, bg=COLORS['bg_dark'])
        info_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            info_frame,
            text="• Laba dari admin pembelian: 2% dari nilai transaksi",
            font=FONTS['small'],
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_muted']
        ).pack(anchor='w', padx=10)
        
        tk.Label(
            info_frame,
            text="• Nilai aset emas = Stok token × Harga emas terkini",
            font=FONTS['small'],
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_muted']
        ).pack(anchor='w', padx=10)
    
    def create_stat_card(self, parent, title, value, unit):
        """Buat card statistik"""
        card = tk.Frame(parent, bg=COLORS['bg_card'], relief=tk.FLAT, bd=1)
        
        title_label = tk.Label(
            card,
            text=title,
            font=FONTS['small'],
            bg=COLORS['bg_card'],
            fg=COLORS['fg_muted']
        )
        title_label.pack(pady=(15, 5))
        
        value_label = tk.Label(
            card,
            text=value,
            font=('Playfair Display', 24, 'bold'),
            bg=COLORS['bg_card'],
            fg=COLORS['accent']
        )
        value_label.pack()
        
        unit_label = tk.Label(
            card,
            text=unit,
            font=FONTS['small'],
            bg=COLORS['bg_card'],
            fg=COLORS['fg_muted']
        )
        unit_label.pack(pady=(5, 15))
        
        card.value_label = value_label
        
        return card
    
    def create_users_tab(self):
        """Buat tab Users"""
        tab = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        self.notebook.add(tab, text="👥 Users")
        
        # Form tambah user
        form_frame = tk.LabelFrame(
            tab,
            text="➕ Tambah User Baru",
            bg=COLORS['bg_dark'],
            fg=COLORS['accent'],
            font=FONTS['heading']
        )
        form_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Username
        tk.Label(
            form_frame,
            text="Username:",
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_text']
        ).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        
        self.user_username = tk.Entry(
            form_frame,
            width=30,
            bg=COLORS['bg_input'],
            fg=COLORS['fg_text'],
            relief=tk.FLAT
        )
        self.user_username.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        # Email
        tk.Label(
            form_frame,
            text="Email:",
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_text']
        ).grid(row=1, column=0, padx=5, pady=5, sticky='w')
        
        self.user_email = tk.Entry(
            form_frame,
            width=30,
            bg=COLORS['bg_input'],
            fg=COLORS['fg_text'],
            relief=tk.FLAT
        )
        self.user_email.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        
        # Nama Lengkap
        tk.Label(
            form_frame,
            text="Nama Lengkap:",
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_text']
        ).grid(row=2, column=0, padx=5, pady=5, sticky='w')
        
        self.user_fullname = tk.Entry(
            form_frame,
            width=30,
            bg=COLORS['bg_input'],
            fg=COLORS['fg_text'],
            relief=tk.FLAT
        )
        self.user_fullname.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        # Buttons
        btn_frame = tk.Frame(form_frame, bg=COLORS['bg_dark'])
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.add_user_btn = tk.Button(
            btn_frame,
            text="➕ Tambah User",
            bg=COLORS['accent'],
            fg=COLORS['bg_dark'],
            font=FONTS['normal'],
            padx=20,
            pady=5,
            relief=tk.FLAT,
            cursor='hand2',
            command=self.add_user
        )
        self.add_user_btn.pack(side=tk.LEFT, padx=5)
        
        self.create_users_table(tab)
    
    def create_users_table(self, parent):
        """Buat tabel users"""
        frame = tk.LabelFrame(
            parent,
            text="📋 Daftar User",
            bg=COLORS['bg_dark'],
            fg=COLORS['accent'],
            font=FONTS['heading']
        )
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('id', 'username', 'full_name', 'email', 'created_at')
        self.users_tree = ttk.Treeview(
            frame,
            columns=columns,
            show='headings',
            height=15
        )
        
        self.users_tree.heading('id', text='ID')
        self.users_tree.heading('username', text='Username')
        self.users_tree.heading('full_name', text='Nama')
        self.users_tree.heading('email', text='Email')
        self.users_tree.heading('created_at', text='Dibuat')
        
        self.users_tree.column('id', width=50)
        self.users_tree.column('username', width=120)
        self.users_tree.column('full_name', width=150)
        self.users_tree.column('email', width=200)
        self.users_tree.column('created_at', width=150)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=scrollbar.set)
        
        self.users_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
    
    def create_anggota_tab(self):
        """Buat tab Anggota"""
        tab = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        self.notebook.add(tab, text="🎫 Anggota")
        
        # Form daftar anggota
        form_frame = tk.LabelFrame(
            tab,
            text="🎫 Daftar Anggota Baru",
            bg=COLORS['bg_dark'],
            fg=COLORS['accent'],
            font=FONTS['heading']
        )
        form_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            form_frame,
            text="User ID:",
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_text']
        ).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        
        self.anggota_user_id = tk.Entry(
            form_frame,
            width=20,
            bg=COLORS['bg_input'],
            fg=COLORS['fg_text'],
            relief=tk.FLAT
        )
        self.anggota_user_id.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        self.add_anggota_btn = tk.Button(
            form_frame,
            text="🎫 Daftar Anggota (Rp 12.000)",
            bg=COLORS['accent'],
            fg=COLORS['bg_dark'],
            font=FONTS['normal'],
            padx=20,
            pady=5,
            relief=tk.FLAT,
            cursor='hand2',
            command=self.daftar_anggota
        )
        self.add_anggota_btn.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.create_anggota_table(tab)
    
    def create_anggota_table(self, parent):
        """Buat tabel anggota"""
        frame = tk.LabelFrame(
            parent,
            text="📋 Daftar Anggota",
            bg=COLORS['bg_dark'],
            fg=COLORS['accent'],
            font=FONTS['heading']
        )
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('id', 'nomor', 'nama', 'status', 'saldo_iuran', 'token')
        self.anggota_tree = ttk.Treeview(
            frame,
            columns=columns,
            show='headings',
            height=15
        )
        
        self.anggota_tree.heading('id', text='ID')
        self.anggota_tree.heading('nomor', text='Nomor Anggota')
        self.anggota_tree.heading('nama', text='Nama')
        self.anggota_tree.heading('status', text='Status')
        self.anggota_tree.heading('saldo_iuran', text='Saldo Iuran')
        self.anggota_tree.heading('token', text='Token')
        
        self.anggota_tree.column('id', width=50)
        self.anggota_tree.column('nomor', width=150)
        self.anggota_tree.column('nama', width=150)
        self.anggota_tree.column('status', width=80)
        self.anggota_tree.column('saldo_iuran', width=120)
        self.anggota_tree.column('token', width=80)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.anggota_tree.yview)
        self.anggota_tree.configure(yscrollcommand=scrollbar.set)
        
        self.anggota_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
    
    def create_token_tab(self):
        """Buat tab Token"""
        tab = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        self.notebook.add(tab, text="🪙 Token")
        
        # Info Token
        info_frame = tk.LabelFrame(
            tab,
            text="📊 Info Token",
            bg=COLORS['bg_dark'],
            fg=COLORS['accent'],
            font=FONTS['heading']
        )
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.stok_token_label = tk.Label(
            info_frame,
            text="Stok Token: 0",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['fg_text'],
            padx=10,
            pady=5
        )
        self.stok_token_label.pack(fill=tk.X, padx=5, pady=5)
        
        self.token_beredar_label = tk.Label(
            info_frame,
            text="Token Beredar: 0",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['success'],
            padx=10,
            pady=5
        )
        self.token_beredar_label.pack(fill=tk.X, padx=5, pady=5)
        
        # Form beli token (simulasi)
        beli_frame = tk.LabelFrame(
            tab,
            text="💰 Simulasi Beli Token",
            bg=COLORS['bg_dark'],
            fg=COLORS['accent'],
            font=FONTS['heading']
        )
        beli_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            beli_frame,
            text="Nomor Anggota:",
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_text']
        ).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        
        self.beli_nomor = tk.Entry(
            beli_frame,
            width=20,
            bg=COLORS['bg_input'],
            fg=COLORS['fg_text'],
            relief=tk.FLAT
        )
        self.beli_nomor.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        tk.Label(
            beli_frame,
            text="Jumlah Token:",
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_text']
        ).grid(row=1, column=0, padx=5, pady=5, sticky='w')
        
        self.beli_jumlah = tk.Entry(
            beli_frame,
            width=20,
            bg=COLORS['bg_input'],
            fg=COLORS['fg_text'],
            relief=tk.FLAT
        )
        self.beli_jumlah.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        self.beli_jumlah.insert(0, "10")
        
        tk.Button(
            beli_frame,
            text="💳 Beli Token",
            bg=COLORS['success'],
            fg=COLORS['bg_dark'],
            font=FONTS['normal'],
            padx=20,
            pady=5,
            relief=tk.FLAT,
            cursor='hand2',
            command=self.beli_token
        ).grid(row=2, column=0, columnspan=2, pady=10)
    
    def create_emas_tab(self):
        """Buat tab Emas"""
        tab = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        self.notebook.add(tab, text="🏆 Emas")
        
        # Info Emas
        info_frame = tk.LabelFrame(
            tab,
            text="📊 Info Emas Fisik",
            bg=COLORS['bg_dark'],
            fg=COLORS['accent'],
            font=FONTS['heading']
        )
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.emas_total_label = tk.Label(
            info_frame,
            text="Total Emas: 0 gram",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['fg_text'],
            padx=10,
            pady=5
        )
        self.emas_total_label.pack(fill=tk.X, padx=5, pady=5)
        
        self.emas_nilai_label = tk.Label(
            info_frame,
            text="Nilai: Rp 0",
            font=FONTS['normal'],
            bg=COLORS['bg_card'],
            fg=COLORS['accent'],
            padx=10,
            pady=5
        )
        self.emas_nilai_label.pack(fill=tk.X, padx=5, pady=5)
        
        # Form tambah emas
        tambah_frame = tk.LabelFrame(
            tab,
            text="➕ Tambah Emas Fisik",
            bg=COLORS['bg_dark'],
            fg=COLORS['accent'],
            font=FONTS['heading']
        )
        tambah_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            tambah_frame,
            text="Jumlah (gram):",
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_text']
        ).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        
        self.emas_jumlah = tk.Entry(
            tambah_frame,
            width=20,
            bg=COLORS['bg_input'],
            fg=COLORS['fg_text'],
            relief=tk.FLAT
        )
        self.emas_jumlah.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.emas_jumlah.insert(0, "1.0")
        
        tk.Label(
            tambah_frame,
            text="Sumber:",
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_text']
        ).grid(row=1, column=0, padx=5, pady=5, sticky='w')
        
        self.emas_sumber = ttk.Combobox(
            tambah_frame,
            values=['modal_awal', 'laba', 'tabungan_anggota', 'investasi', 'donasi', 'lainnya'],
            width=18,
            state='readonly'
        )
        self.emas_sumber.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        self.emas_sumber.set('laba')
        
        tk.Label(
            tambah_frame,
            text="Keterangan:",
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_text']
        ).grid(row=2, column=0, padx=5, pady=5, sticky='w')
        
        self.emas_keterangan = tk.Entry(
            tambah_frame,
            width=30,
            bg=COLORS['bg_input'],
            fg=COLORS['fg_text'],
            relief=tk.FLAT
        )
        self.emas_keterangan.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        tk.Button(
            tambah_frame,
            text="💎 Tambah Emas",
            bg=COLORS['accent'],
            fg=COLORS['bg_dark'],
            font=FONTS['normal'],
            padx=20,
            pady=5,
            relief=tk.FLAT,
            cursor='hand2',
            command=self.tambah_emas
        ).grid(row=3, column=0, columnspan=2, pady=10)
        
        tk.Button(
            tambah_frame,
            text="🏁 Inisialisasi Emas Awal (1 gram)",
            bg=COLORS['warning'],
            fg=COLORS['bg_dark'],
            font=FONTS['normal'],
            padx=20,
            pady=5,
            relief=tk.FLAT,
            cursor='hand2',
            command=self.init_emas_awal
        ).grid(row=4, column=0, columnspan=2, pady=5)
        
        # Riwayat emas
        riwayat_frame = tk.LabelFrame(
            tab,
            text="📋 Riwayat Penambahan Emas",
            bg=COLORS['bg_dark'],
            fg=COLORS['accent'],
            font=FONTS['heading']
        )
        riwayat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('tanggal', 'jumlah', 'sumber', 'keterangan')
        self.emas_tree = ttk.Treeview(
            riwayat_frame,
            columns=columns,
            show='headings',
            height=8
        )
        
        self.emas_tree.heading('tanggal', text='Tanggal')
        self.emas_tree.heading('jumlah', text='Jumlah (gram)')
        self.emas_tree.heading('sumber', text='Sumber')
        self.emas_tree.heading('keterangan', text='Keterangan')
        
        self.emas_tree.column('tanggal', width=150)
        self.emas_tree.column('jumlah', width=100)
        self.emas_tree.column('sumber', width=150)
        self.emas_tree.column('keterangan', width=300)
        
        scrollbar = ttk.Scrollbar(riwayat_frame, orient=tk.VERTICAL, command=self.emas_tree.yview)
        self.emas_tree.configure(yscrollcommand=scrollbar.set)
        
        self.emas_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
    
    def create_settings_tab(self):
        """Buat tab Settings"""
        tab = tk.Frame(self.notebook, bg=COLORS['bg_dark'])
        self.notebook.add(tab, text="⚙️ Settings")
        
        # Server Settings
        server_frame = tk.LabelFrame(
            tab,
            text="🔌 Server",
            bg=COLORS['bg_dark'],
            fg=COLORS['accent'],
            font=FONTS['heading']
        )
        server_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            server_frame,
            text=f"API URL: {API_URL}",
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_muted'],
            font=FONTS['normal'],
            padx=10,
            pady=5
        ).pack(anchor='w')
        
        # Auto Refresh
        refresh_frame = tk.LabelFrame(
            tab,
            text="⏱️ Auto Refresh",
            bg=COLORS['bg_dark'],
            fg=COLORS['accent'],
            font=FONTS['heading']
        )
        refresh_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.auto_refresh_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            refresh_frame,
            text=f"Aktifkan auto refresh setiap {REFRESH_INTERVAL} detik",
            variable=self.auto_refresh_var,
            bg=COLORS['bg_dark'],
            fg=COLORS['fg_text'],
            selectcolor=COLORS['bg_input'],
            activebackground=COLORS['bg_dark'],
            command=self.toggle_auto_refresh
        ).pack(anchor='w', padx=10, pady=5)
        
        # Reset Database
        reset_frame = tk.LabelFrame(
            tab,
            text="⚠️ Bahaya",
            bg=COLORS['bg_dark'],
            fg=COLORS['error'],
            font=FONTS['heading']
        )
        reset_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(
            reset_frame,
            text="🗑️ RESET DATABASE",
            bg=COLORS['error'],
            fg='white',
            font=FONTS['normal'],
            padx=20,
            pady=10,
            relief=tk.FLAT,
            cursor='hand2',
            command=self.reset_database
        ).pack(pady=10)
    
    # ====================================================
    # FUNGSI-FUNGSI
    # ====================================================
    
    def check_server(self):
        """Cek koneksi ke server"""
        try:
            result = api_get("/")
            if result and not isinstance(result, dict) or not result.get('error'):
                self.status_server.config(
                    text="✅ Server: ONLINE",
                    fg=COLORS['success']
                )
                return True
            else:
                self.status_server.config(
                    text="❌ Server: ERROR",
                    fg=COLORS['error']
                )
                return False
        except:
            self.status_server.config(
                text="❌ Server: OFFLINE",
                fg=COLORS['error']
            )
            return False
    
    def update_status(self, message):
        """Update status bar"""
        self.status_text.config(text=message)
        self.last_update.config(
            text=f"Update: {datetime.now().strftime('%H:%M:%S')}"
        )
    
    def toggle_auto_refresh(self):
        """Toggle auto refresh"""
        self.auto_refresh = self.auto_refresh_var.get()
    
    def add_user(self):
        """Tambah user baru"""
        username = self.user_username.get().strip()
        email = self.user_email.get().strip()
        fullname = self.user_fullname.get().strip()
        
        if not username or not email or not fullname:
            messagebox.showwarning("Peringatan", "Semua field harus diisi!")
            return
        
        params = {
            'username': username,
            'email': email,
            'full_name': fullname
        }
        
        result = api_post("/user/register", params)
        
        if result.get('error'):
            messagebox.showerror("Error", result['error'])
        elif result.get('success'):
            messagebox.showinfo("Sukses", "User berhasil ditambahkan!")
            self.user_username.delete(0, tk.END)
            self.user_email.delete(0, tk.END)
            self.user_fullname.delete(0, tk.END)
            self.load_users()
        else:
            messagebox.showerror("Error", "Gagal menambah user")
    
    def daftar_anggota(self):
        """Daftar anggota baru"""
        user_id = self.anggota_user_id.get().strip()
        
        if not user_id:
            messagebox.showwarning("Peringatan", "User ID harus diisi!")
            return
        
        try:
            user_id = int(user_id)
        except:
            messagebox.showwarning("Peringatan", "User ID harus angka!")
            return
        
        result = api_post(f"/anggota/daftar?user_id={user_id}")
        
        if result.get('error'):
            messagebox.showerror("Error", result['error'])
        elif result.get('success'):
            messagebox.showinfo("Sukses", result['message'])
            self.anggota_user_id.delete(0, tk.END)
            self.load_anggota()
            self.load_dashboard()
        else:
            messagebox.showerror("Error", "Gagal mendaftar")
    
    def beli_token(self):
        """Simulasi beli token"""
        nomor = self.beli_nomor.get().strip()
        jumlah = self.beli_jumlah.get().strip()
        
        if not nomor or not jumlah:
            messagebox.showwarning("Peringatan", "Nomor anggota dan jumlah harus diisi!")
            return
        
        try:
            jumlah = int(jumlah)
        except:
            messagebox.showwarning("Peringatan", "Jumlah harus angka!")
            return
        
        result = api_post(f"/token/beli?nomor_anggota={nomor}&jumlah_token={jumlah}")
        
        if result.get('error'):
            messagebox.showerror("Error", result['error'])
        elif result.get('success'):
            messagebox.showinfo("Sukses", result['message'])
            self.load_anggota()
            self.load_stok_token()
            self.load_dashboard()
        else:
            messagebox.showerror("Error", "Gagal beli token")
    
    def tambah_emas(self):
        """Tambah emas fisik"""
        try:
            jumlah = float(self.emas_jumlah.get().strip())
            if jumlah <= 0:
                messagebox.showwarning("Peringatan", "Jumlah harus positif!")
                return
        except ValueError:
            messagebox.showwarning("Peringatan", "Jumlah harus angka!")
            return
        
        sumber = self.emas_sumber.get()
        keterangan = self.emas_keterangan.get().strip()
        
        result = api_post(
            f"/admin/emas-fisik/tambah?jumlah_gram={jumlah}&sumber={sumber}&keterangan={keterangan}"
        )
        
        if result.get('error'):
            messagebox.showerror("Error", result['error'])
        elif result.get('status') == 'success':
            messagebox.showinfo("Sukses", result['message'])
            self.emas_jumlah.delete(0, tk.END)
            self.emas_jumlah.insert(0, "1.0")
            self.emas_keterangan.delete(0, tk.END)
            self.load_emas()
            self.load_stok_token()
            self.load_dashboard()
        else:
            messagebox.showerror("Error", "Gagal tambah emas")
    
    def init_emas_awal(self):
        """Inisialisasi emas awal 1 gram"""
        if not messagebox.askyesno("Konfirmasi", "Inisialisasi emas awal 1 gram? Lakukan hanya sekali!"):
            return
        
        result = api_post("/admin/emas-fisik/init")
        
        if result.get('error'):
            messagebox.showerror("Error", result['error'])
        elif result.get('status') == 'success':
            messagebox.showinfo("Sukses", result['message'])
            self.load_emas()
            self.load_stok_token()
            self.load_dashboard()
        else:
            messagebox.showerror("Error", "Gagal inisialisasi")
    
    def reset_database(self):
        """Reset database (HATI-HATI!)"""
        if not messagebox.askyesno(
            "PERINGATAN!",
            "RESET DATABASE akan menghapus SEMUA data!\n\n"
            "• Semua user\n"
            "• Semua anggota\n"
            "• Semua token\n"
            "• Semua transaksi\n\n"
            "Yakin ingin melanjutkan?",
            icon='warning'
        ):
            return
        
        if not messagebox.askyesno("Konfirmasi Terakhir", "Ini tindakan terakhir. Yakin?"):
            return
        
        result = api_post("/admin/reset")
        
        if result.get('error'):
            messagebox.showerror("Error", result['error'])
        elif result.get('status') == 'success':
            messagebox.showinfo("Sukses", "Database telah direset")
            self.refresh_all()
        else:
            messagebox.showerror("Error", "Gagal reset database")
    
    def load_laba(self):
        """Load data laba dari API"""
        try:
            # Ambil data transaksi untuk menghitung laba
            # Dalam implementasi nyata, ini dari endpoint khusus
            
            # Untuk demo, kita gunakan data dari API yang ada
            # Laba dari pembelian token (2% dari nilai transaksi)
            laba_beli = 50000  # Contoh, nanti diganti dengan data real
            laba_jual = 75000  # Contoh
            
            self.laba_beli_token.config(text=format_rupiah(laba_beli))
            self.laba_jual_token.config(text=format_rupiah(laba_jual))
            
            total_token = laba_beli + laba_jual
            self.total_laba_token.config(text=format_rupiah(total_token))
            
            # Total seluruh laba (hanya dari admin token untuk sekarang)
            self.total_laba_all.config(text=format_rupiah(total_token))
            
        except Exception as e:
            print(f"Error load laba: {e}")
    
    def load_aset_emas(self):
        """Load dan hitung aset emas (Stok token × Harga emas)"""
        try:
            # Ambil stok token
            stok_result = api_get("/admin/stok-token")
            stok = stok_result.get('stok_token', 0) if isinstance(stok_result, dict) else 0
            
            # Ambil harga emas
            harga_result = api_get("/harga")
            harga = 0
            if isinstance(harga_result, dict) and 'emas' in harga_result:
                harga = harga_result['emas'].get('per_gram', 0)
            
            # Hitung aset
            aset = stok * harga
            
            # Update UI
            self.stok_token_aset.config(text=f"{stok} token")
            self.harga_emas_aset.config(text=format_rupiah(harga))
            self.total_aset_emas.config(text=format_rupiah(aset))
            
            # Update juga di stat card
            if "📈 Harga Emas" in self.stats:
                self.stats["📈 Harga Emas"].value_label.config(text=format_rupiah(harga))
            
        except Exception as e:
            print(f"Error load aset emas: {e}")
    
    def load_users(self):
        """Load data users dari API"""
        try:
            result = api_get("/admin/users")
            
            if result.get('error'):
                self.update_status(f"❌ Gagal: {result['error']}")
                return
            
            # Clear existing
            for item in self.users_tree.get_children():
                self.users_tree.delete(item)
            
            # Insert data
            users = result.get('data', [])
            for user in users:
                self.users_tree.insert('', tk.END, values=(
                    user['id'],
                    user['username'],
                    user['full_name'],
                    user['email'],
                    user['created_at'][:10] if user['created_at'] else '-'
                ))
            
            self.update_status(f"✅ {len(users)} user dimuat")
            
        except Exception as e:
            self.update_status(f"❌ Error: {str(e)}")
    
    def load_anggota(self):
        """Load data anggota dari API"""
        try:
            result = api_get("/admin/anggota")
            
            if result.get('error'):
                self.update_status(f"❌ Gagal: {result['error']}")
                return
            
            # Clear existing
            for item in self.anggota_tree.get_children():
                self.anggota_tree.delete(item)
            
            # Insert data
            anggota_list = result.get('data', [])
            for anggota in anggota_list:
                status = "✅ Aktif" if anggota['status'] == 'aktif' else "⏳ Nonaktif"
                
                self.anggota_tree.insert('', tk.END, values=(
                    anggota['id'],
                    anggota['nomor_anggota'],
                    anggota['nama'],
                    status,
                    format_rupiah(anggota['saldo_iuran']),
                    anggota['token_sukarela']
                ))
            
            self.update_status(f"✅ {len(anggota_list)} anggota dimuat")
            
        except Exception as e:
            self.update_status(f"❌ Error: {str(e)}")
    
    def load_stok_token(self):
        """Load data stok token"""
        try:
            result = api_get("/admin/stok-token")
            
            if result.get('error'):
                return
            
            stok = result.get('stok_token', 0)
            self.stok_token_label.config(text=f"Stok Token: {stok}")
            
            # Update dashboard juga
            if "🪙 Stok Token" in self.stats:
                self.stats["🪙 Stok Token"].value_label.config(text=str(stok))
            
            # Update aset emas
            self.load_aset_emas()
            
        except Exception as e:
            print(f"Error load stok token: {e}")
    
    def load_emas(self):
        """Load data emas fisik dari API"""
        try:
            result = api_get("/admin/emas-fisik")
            
            if result.get('error'):
                self.update_status(f"❌ Gagal: {result['error']}")
                return
            
            # Update info
            total_gram = result.get('total_gram', 0)
            nilai_total = result.get('nilai_total_rupiah', 0)
            
            self.emas_total_label.config(
                text=f"Total Emas: {total_gram:.2f} gram"
            )
            self.emas_nilai_label.config(
                text=f"Nilai: {format_rupiah(nilai_total)}"
            )
            
            # Clear tree
            for item in self.emas_tree.get_children():
                self.emas_tree.delete(item)
            
            # Insert riwayat
            riwayat = result.get('data', [])
            for r in riwayat:
                tanggal = r.get('tanggal', '')[:10] if r.get('tanggal') else '-'
                self.emas_tree.insert('', tk.END, values=(
                    tanggal,
                    f"{r.get('jumlah_gram', 0):.2f}",
                    r.get('sumber', '-'),
                    r.get('keterangan', '-')
                ))
            
        except Exception as e:
            self.update_status(f"❌ Error: {str(e)}")
    
    def load_dashboard(self):
        """Load data dashboard"""
        try:
            result = api_get("/admin/dashboard")
            
            if result.get('error'):
                return
            
            stats = result.get('statistik', {})
            
            # Update stat cards
            if "👥 Anggota Aktif" in self.stats:
                self.stats["👥 Anggota Aktif"].value_label.config(
                    text=stats.get('anggota', {}).get('aktif', 0)
                )
            
            if "🪙 Stok Token" in self.stats:
                self.stats["🪙 Stok Token"].value_label.config(
                    text=stats.get('stok_token', 0)
                )
            
            if "💰 Total Kas" in self.stats:
                keuangan = stats.get('keuangan', {})
                self.stats["💰 Total Kas"].value_label.config(
                    text=format_rupiah(keuangan.get('total_iuran', 0))
                )
            
            # Load laba dan aset
            self.load_laba()
            self.load_aset_emas()
            
        except Exception as e:
            print(f"Error load dashboard: {e}")
    
    def refresh_all(self):
        """Refresh semua data"""
        self.update_status("Merefresh data...")
        self.check_server()
        self.load_dashboard()
        self.load_users()
        self.load_anggota()
        self.load_stok_token()
        self.load_emas()
        self.update_status("✅ Data diperbarui")
    
    def after_load(self):
        """Dipanggil setelah UI selesai"""
        self.refresh_all()
    
    def auto_refresh_loop(self):
        """Loop untuk auto refresh"""
        while self.auto_refresh:
            time.sleep(REFRESH_INTERVAL)
            if self.auto_refresh:
                self.root.after(0, self.refresh_all)
    
    def start_auto_refresh(self):
        """Mulai auto refresh thread"""
        self.refresh_thread = threading.Thread(target=self.auto_refresh_loop, daemon=True)
        self.refresh_thread.start()
    
    def on_closing(self):
        """Event saat window ditutup"""
        self.auto_refresh = False
        if self.refresh_thread:
            self.refresh_thread.join(timeout=1)
        self.root.destroy()

# ====================================================
# MAIN
# ====================================================
def main():
    root = tk.Tk()
    app = AdminDesktop(root)
    root.mainloop()

if __name__ == "__main__":
    main()