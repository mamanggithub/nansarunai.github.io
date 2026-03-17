/**
 * script.js - Website Publik Koperasi Token Emas
 * Menampilkan info koperasi, harga emas, kurs, dan grafik dengan sumbu X berdasarkan jam
 * Update harga setiap 5 menit, update grafik setiap jam
 */

// ====================================================
// KONFIGURASI
// ====================================================
const API_URL = 'http://localhost:8000';

// Data untuk grafik
let emasChart, kursChart;
let historicalData = [];
let lastChartUpdate = 0;

// ====================================================
// FUNGSI AMBIL DATA DARI BACKEND
// ====================================================

/**
 * Ambil info koperasi dari endpoint /info
 */
async function fetchInfoKoperasi() {
    console.log('📡 Mengambil info koperasi...');
    try {
        const response = await fetch(`${API_URL}/info`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('✅ Info koperasi:', data);
        updateUI(data);
        return data;
    } catch (error) {
        console.error('❌ Error fetching info:', error);
    }
}

/**
 * Ambil harga emas dan kurs dari endpoint /harga
 */
async function fetchHarga() {
    console.log('📡 Mengambil data harga...');
    try {
        const response = await fetch(`${API_URL}/harga`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('✅ Data harga:', data);
        updateHargaUI(data);
        return data;
    } catch (error) {
        console.error('❌ Error fetching harga:', error);
    }
}

/**
 * Ambil data dashboard dari endpoint /admin/dashboard
 */
async function fetchDashboard() {
    console.log('📡 Mengambil data dashboard...');
    try {
        const response = await fetch(`${API_URL}/admin/dashboard`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('✅ Data dashboard:', data);
        updateDashboardUI(data);
        return data;
    } catch (error) {
        console.error('❌ Error fetching dashboard:', error);
    }
}

/**
 * Ambil data historis dari endpoint /historical
 */
async function fetchHistoricalData() {
    console.log('📡 Mengambil data historis...');
    try {
        const response = await fetch(`${API_URL}/historical?days=7`);
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Data historis:', data);
            return data;
        }
    } catch (error) {
        console.error('❌ Error fetching historical data:', error);
    }
    
    // Fallback ke data default jika API gagal
    console.log('📊 Menggunakan data default');
    const now = new Date();
    const data = [];
    for (let i = 6; i >= 0; i--) {
        const date = new Date(now);
        date.setHours(date.getHours() - i * 24);
        data.push({
            date_display: date.toLocaleString('id-ID', { 
                hour: '2-digit', 
                minute: '2-digit',
                day: '2-digit',
                month: '2-digit'
            }),
            emas: 2700000 + Math.random() * 50000,
            kurs: 15500 + Math.random() * 100
        });
    }
    return data;
}

// ====================================================
// FUNGSI UPDATE UI
// ====================================================

function updateUI(data) {
    console.log('🔄 Update UI dengan data:', data);
    
    // Update hero stats
    updateElementText('totalAnggota', data.statistik?.total_anggota_aktif || 0);
    updateElementText('stokToken', data.statistik?.stok_token || 0);
    
    const emasStr = data.statistik?.total_emas_fisik || '0 gram';
    updateElementText('totalEmas', emasStr.split(' ')[0]);
    
    // Update about stats
    updateElementText('anggotaAktif', data.statistik?.total_anggota_aktif || 0);
    updateElementText('stokTokenStat', data.statistik?.stok_token || 0);
    updateElementText('emasFisik', emasStr.split(' ')[0]);
    
    let nilaiEmas = data.statistik?.nilai_emas || '0';
    if (typeof nilaiEmas === 'string') {
        nilaiEmas = nilaiEmas.replace(/[^0-9]/g, '');
    }
    updateElementText('nilaiEmas', nilaiEmas);
}

function updateHargaUI(data) {
    console.log('🔄 Update UI dengan data harga:', data);
    
    if (data.emas) {
        updateElementText('hargaEmas', data.emas.formatted || 'Rp 0');
    }
    
    if (data.kurs) {
        updateElementText('kursUSD', data.kurs.formatted || 'Rp 0');
    }
    
    // Update waktu
    const now = new Date().toLocaleTimeString('id-ID');
    updateElementText('updateEmas', `Update: ${now}`);
    updateElementText('updateKurs', `Update: ${now}`);
}

function updateDashboardUI(data) {
    console.log('🔄 Update dashboard UI:', data);
    
    const stats = data.statistik || {};
    
    updateElementText('totalUser', stats.user?.total || 0);
    updateElementText('totalAnggotaFull', stats.anggota?.total || 0);
    updateElementText('anggotaAktifFull', stats.anggota?.aktif || 0);
    updateElementText('stokTokenFull', stats.stok_token || 0);
    
    const emasGram = stats.emas_fisik?.total_gram || 0;
    updateElementText('emasFisikFull', emasGram.toFixed(2));
    
    const totalIuran = stats.keuangan?.total_iuran || 0;
    updateElementText('totalIuran', totalIuran.toLocaleString('id-ID'));
}

function updateElementText(id, text) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = text;
    } else {
        console.warn(`Element dengan id ${id} tidak ditemukan`);
    }
}

// ====================================================
// FUNGSI GRAFIK DENGAN SUMBU X BERDASARKAN JAM
// ====================================================

/**
 * Format tanggal untuk sumbu X (jam:menit)
 */
function formatTimeLabel(date) {
    return date.toLocaleTimeString('id-ID', { 
        hour: '2-digit', 
        minute: '2-digit'
    });
}

/**
 * Generate data historis berdasarkan jam
 */
function generateHourlyData(basePrice, baseKurs, hours = 24) {
    const data = [];
    const now = new Date();
    
    for (let i = hours; i >= 0; i--) {
        const date = new Date(now);
        date.setHours(date.getHours() - i);
        
        // Variasi kecil untuk simulasi
        const emasVariation = 1 + (Math.random() * 0.02 - 0.01);
        const kursVariation = 1 + (Math.random() * 0.01 - 0.005);
        
        data.push({
            label: formatTimeLabel(date),
            emas: basePrice * emasVariation,
            kurs: baseKurs * kursVariation,
            timestamp: date.getTime()
        });
    }
    
    return data;
}

async function initCharts() {
    console.log('📊 Inisialisasi grafik dengan sumbu X berdasarkan jam...');
    
    // Ambil data harga terkini untuk base
    let basePrice = 2700000;
    let baseKurs = 15500;
    
    try {
        const harga = await fetchHarga();
        if (harga && harga.emas) {
            basePrice = harga.emas.per_gram || basePrice;
        }
        if (harga && harga.kurs) {
            baseKurs = harga.kurs.usd_to_idr || baseKurs;
        }
    } catch (error) {
        console.warn('Gagal ambil harga, gunakan default');
    }
    
    // Generate data per jam
    const chartData = generateHourlyData(basePrice, baseKurs, 24);
    historicalData = chartData;
    
    const labels = chartData.map(d => d.label);
    
    // Grafik Emas
    const emasCtx = document.getElementById('emasChart');
    if (!emasCtx) {
        console.warn('Canvas emasChart tidak ditemukan');
        return;
    }
    
    emasChart = new Chart(emasCtx.getContext('2d'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Harga Emas (IDR/gram)',
                data: chartData.map(d => d.emas),
                borderColor: '#ffd700',
                backgroundColor: 'rgba(255, 215, 0, 0.1)',
                borderWidth: 2,
                pointRadius: 2,
                pointBackgroundColor: '#ffd700',
                tension: 0.2,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    labels: { color: '#e5e7eb' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Rp ' + context.parsed.y.toLocaleString('id-ID');
                        }
                    }
                }
            },
            scales: {
                y: {
                    ticks: { 
                        color: '#9ca3af',
                        callback: function(value) {
                            return 'Rp ' + value.toLocaleString('id-ID');
                        }
                    },
                    grid: { color: '#2a3038' }
                },
                x: {
                    ticks: { 
                        color: '#9ca3af',
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: { color: '#2a3038' },
                    title: {
                        display: true,
                        text: 'Waktu (Jam)',
                        color: '#9ca3af'
                    }
                }
            }
        }
    });
    
    // Grafik Kurs
    const kursCtx = document.getElementById('kursChart');
    if (!kursCtx) {
        console.warn('Canvas kursChart tidak ditemukan');
        return;
    }
    
    kursChart = new Chart(kursCtx.getContext('2d'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Kurs USD/IDR',
                data: chartData.map(d => d.kurs),
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                pointRadius: 2,
                pointBackgroundColor: '#3b82f6',
                tension: 0.2,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    labels: { color: '#e5e7eb' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Rp ' + context.parsed.y.toLocaleString('id-ID');
                        }
                    }
                }
            },
            scales: {
                y: {
                    ticks: { 
                        color: '#9ca3af',
                        callback: function(value) {
                            return 'Rp ' + value.toLocaleString('id-ID');
                        }
                    },
                    grid: { color: '#2a3038' }
                },
                x: {
                    ticks: { 
                        color: '#9ca3af',
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: { color: '#2a3038' },
                    title: {
                        display: true,
                        text: 'Waktu (Jam)',
                        color: '#9ca3af'
                    }
                }
            }
        }
    });
    
    console.log('✅ Grafik berhasil diinisialisasi');
    lastChartUpdate = Date.now();
}

/**
 * Update grafik dengan data baru (dipanggil setiap jam)
 */
async function updateChartsWithNewData() {
    console.log('📈 Mengupdate grafik dengan data baru (per jam)...');
    
    // Cek apakah sudah 1 jam sejak update terakhir
    const now = Date.now();
    if (now - lastChartUpdate < 3600000) { // 1 jam = 3600000 ms
        console.log('⏳ Belum waktunya update grafik (masih < 1 jam)');
        return;
    }
    
    try {
        // Ambil data historis terbaru
        const newData = await fetchHistoricalData();
        
        if (newData && newData.length > 0) {
            historicalData = newData;
            
            const labels = newData.map(d => d.date_display);
            
            if (emasChart) {
                emasChart.data.labels = labels;
                emasChart.data.datasets[0].data = newData.map(d => d.emas);
                emasChart.update();
            }
            
            if (kursChart) {
                kursChart.data.labels = labels;
                kursChart.data.datasets[0].data = newData.map(d => d.kurs);
                kursChart.update();
            }
            
            console.log('✅ Grafik diupdate');
            lastChartUpdate = now;
        } else {
            // Fallback: generate data baru berdasarkan harga terkini
            const harga = await fetchHarga();
            const basePrice = harga?.emas?.per_gram || 2700000;
            const baseKurs = harga?.kurs?.usd_to_idr || 15500;
            
            const newChartData = generateHourlyData(basePrice, baseKurs, 24);
            historicalData = newChartData;
            
            const labels = newChartData.map(d => d.label);
            
            if (emasChart) {
                emasChart.data.labels = labels;
                emasChart.data.datasets[0].data = newChartData.map(d => d.emas);
                emasChart.update();
            }
            
            if (kursChart) {
                kursChart.data.labels = labels;
                kursChart.data.datasets[0].data = newChartData.map(d => d.kurs);
                kursChart.update();
            }
            
            console.log('✅ Grafik diupdate dengan data simulasi');
            lastChartUpdate = now;
        }
    } catch (error) {
        console.error('❌ Error updating charts:', error);
    }
}

// ====================================================
// AUTO REFRESH
// ====================================================

// Update data harga setiap 5 menit (300000 ms)
setInterval(() => {
    console.log('⏰ Auto refresh data harga (5 menit)...');
    fetchHarga();
    fetchInfoKoperasi();
    fetchDashboard();
}, 300000);

// Update grafik setiap 1 jam (3600000 ms)
setInterval(() => {
    console.log('⏰ Auto refresh grafik (1 jam)...');
    updateChartsWithNewData();
}, 3600000);

// ====================================================
// NAVBAR TOGGLE
// ====================================================
function initNavbar() {
    const navToggle = document.getElementById('navToggle');
    if (navToggle) {
        navToggle.addEventListener('click', () => {
            const navMenu = document.querySelector('.nav-menu');
            if (navMenu) {
                navMenu.classList.toggle('active');
            }
        });
    }
}

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
                
                const navMenu = document.querySelector('.nav-menu');
                if (navMenu && window.innerWidth <= 768) {
                    navMenu.classList.remove('active');
                }
            }
        });
    });
}

// ====================================================
// INITIALIZATION
// ====================================================
window.addEventListener('load', async () => {
    console.log('🚀 Website Koperasi Token Emas dimuat');
    console.log('🌐 API URL:', API_URL);
    console.log('⏰ Grafik menggunakan sumbu X berdasarkan jam');
    
    initNavbar();
    initSmoothScroll();
    
    // Test koneksi ke server
    try {
        const testResponse = await fetch(API_URL);
        if (testResponse.ok) {
            console.log('✅ Koneksi ke server berhasil');
        } else {
            console.warn('⚠️ Koneksi ke server bermasalah');
        }
    } catch (error) {
        console.error('❌ Tidak dapat terhubung ke server:', error);
    }
    
    // Ambil data harga (prioritas)
    await fetchHarga();
    
    // Ambil info koperasi
    await fetchInfoKoperasi();
    
    // Ambil data dashboard
    await fetchDashboard();
    
    // Inisialisasi grafik
    await initCharts();
    
    // Set waktu awal
    const now = new Date().toLocaleTimeString('id-ID');
    updateElementText('updateEmas', `Update: ${now}`);
    updateElementText('updateKurs', `Update: ${now}`);
    
    console.log('✅ Inisialisasi selesai');
    console.log('📊 Grafik akan diperbarui setiap 1 jam');
});