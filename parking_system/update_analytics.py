import os

content = """{% extends "base.html" %}

{% block content %}
<!DOCTYPE html>
<html lang="vi" class="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phân Tích AI - Smart Parking</title>
    <!-- TailwindCSS v3.4.1 -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: { brand: { 50: '#f0f9ff', 100: '#e0f2fe', 200: '#bae6fd', 300: '#7dd3fc', 400: '#38bdf8', 500: '#0ea5e9', 600: '#0284c7', 700: '#0369a1', 800: '#075985', 900: '#0c4a6e', 950: '#082f49' } },
                    fontFamily: { sans: ['Inter', 'sans-serif'] }
                }
            }
        }
    </script>
    <!-- Google Fonts: Inter -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <!-- FontAwesome v6.4.0 -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Chart.js v4.4.1 -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        body { font-family: 'Inter', sans-serif; }
        .glass-panel {
            background: rgba(255, 255, 255, 0.75);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255,255,255,0.4);
        }
        html.dark .glass-panel {
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid rgba(255,255,255,0.05);
        }
        
        .loading-overlay {
            position: absolute; inset: 0; background: rgba(255,255,255,0.7); backdrop-filter: blur(4px);
            display: flex; align-items: center; justify-content: center; z-index: 10;
        }
        html.dark .loading-overlay { background: rgba(15, 23, 42, 0.7); }
    </style>
</head>
<body class="bg-slate-50 dark:bg-slate-900 text-gray-800 dark:text-gray-200 flex flex-col min-h-screen transition-colors duration-300">

    <!-- Navbar -->
    <nav class="bg-white dark:bg-gray-900 shadow-sm sticky top-0 z-50 transition-colors">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <!-- Branding -->
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 bg-brand-500 rounded-xl flex items-center justify-center shadow-lg shadow-brand-500/30">
                        <i class="fa-solid fa-car text-white text-xl"></i>
                    </div>
                    <div>
                        <span class="font-bold text-xl tracking-tight text-gray-900 dark:text-white leading-none">Smart<span class="text-brand-500">Parking</span></span>
                        <p class="text-[10px] text-gray-500 dark:text-gray-400 uppercase tracking-widest font-semibold mt-0.5">AI Monitoring System</p>
                    </div>
                </div>

                <!-- Navigation Links -->
                <div class="hidden md:flex items-center space-x-1">
                    <a href="/" class="px-4 py-2 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition">
                        <i class="fa-solid fa-video mr-1.5 opacity-70"></i> Live Map
                    </a>
                    <a href="/analytics" class="px-4 py-2 rounded-lg text-sm font-medium bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400 transition">
                        <i class="fa-solid fa-chart-pie mr-1.5 opacity-70"></i> Analytics
                    </a>
                    <a href="/history" class="px-4 py-2 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition">
                        <i class="fa-solid fa-clock-rotate-left mr-1.5 opacity-70"></i> History
                    </a>
                    <a href="/vehicles" class="px-4 py-2 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition">
                        <i class="fa-solid fa-magnifying-glass mr-1.5 opacity-70"></i> Tìm Xe
                    </a>
                    <a href="/manual" class="px-4 py-2 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition">
                        <i class="fa-solid fa-bell-concierge mr-1.5 opacity-70"></i> Quầy Dịch Vụ
                    </a>
                </div>

                <!-- Right Menu -->
                <div class="flex items-center gap-4">
                    <div class="text-sm font-medium text-gray-600 dark:text-gray-300 mr-2">
                        Chào, <span class="text-brand-500 uppercase">{{ current_user.username }}</span>
                    </div>
                    <a href="/logout" class="text-gray-400 hover:text-red-500 transition" title="Đăng xuất">
                        <i class="fa-solid fa-power-off text-lg"></i>
                    </a>
                    <div class="h-6 w-px bg-gray-200 dark:bg-gray-700"></div>
                    <button id="theme-toggle" class="w-9 h-9 flex items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition">
                        <i id="theme-toggle-dark-icon" class="hidden font-bold text-xl fa-solid fa-moon text-gray-700 dark:text-gray-300"></i>
                        <i id="theme-toggle-light-icon" class="hidden font-bold text-xl fa-solid fa-sun text-yellow-500"></i>
                    </button>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="flex-grow max-w-[90rem] mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full transition-opacity" id="dashboard-container">
        
        <!-- Header Title & Tools -->
        <div class="mb-6 flex flex-col md:flex-row md:justify-between md:items-end gap-4 border-b border-gray-200 dark:border-gray-800 pb-5">
            <div>
                <h2 class="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">Báo Cáo Hoạt Động Bãi Đỗ</h2>
                <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">Thống kê doanh thu, lưu lượng và tối ưu hóa hệ thống AI.</p>
            </div>
            
            <form id="filter-form" class="flex flex-wrap items-center gap-3">
                <div class="flex flex-col">
                    <label class="text-xs text-gray-500 mb-1 ml-1 font-semibold" for="start_date">Từ ngày</label>
                    <input type="date" id="start_date" name="start_date" class="rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm py-1.5 px-3 focus:ring-brand-500 focus:border-brand-500 shadow-sm transition">
                </div>
                <div class="flex flex-col">
                    <label class="text-xs text-gray-500 mb-1 ml-1 font-semibold" for="end_date">Đến ngày</label>
                    <input type="date" id="end_date" name="end_date" class="rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm py-1.5 px-3 focus:ring-brand-500 focus:border-brand-500 shadow-sm transition">
                </div>
                <div class="flex items-end gap-2 mt-4 md:mt-0 md:mb-[1px]">
                    <button type="button" onclick="loadData()" class="bg-brand-600 hover:bg-brand-700 text-white rounded-lg px-4 py-1.5 font-medium shadow transition">
                        <i class="fa-solid fa-filter mr-1"></i> Lọc
                    </button>
                    <button type="button" onclick="resetFilters()" class="bg-gray-200 hover:bg-gray-300 text-gray-800 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 rounded-lg px-4 py-1.5 font-medium shadow transition">
                        Đặt lại
                    </button>
                    <button type="button" onclick="exportData()" class="bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg px-4 py-1.5 font-medium shadow transition md:ml-2">
                        <i class="fa-solid fa-file-excel mr-1"></i> Xuất Excel
                    </button>
                </div>
            </form>
        </div>

        <!-- 6 Widget Số Liệu Nhanh -->
        <div class="grid grid-cols-2 lg:grid-cols-6 gap-4 mb-8">
            <div class="glass-panel overflow-hidden rounded-xl p-4 shadow-sm border-l-4 border-l-brand-500">
                <dt class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Tổng Lượt Vào Bãi</dt>
                <dd class="text-2xl font-bold text-gray-900 dark:text-white" id="kpi-total-visits">0</dd>
            </div>
            
            <div class="glass-panel overflow-hidden rounded-xl p-4 shadow-sm border-l-4 border-l-indigo-500">
                <dt class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Xe Đang Đỗ</dt>
                <dd class="text-2xl font-bold text-gray-900 dark:text-white" id="kpi-total-parking">0</dd>
            </div>
            
            <div class="glass-panel overflow-hidden rounded-xl p-4 shadow-sm border-l-4 border-l-yellow-500">
                <dt class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Xe VIP Hiện Diện</dt>
                <dd class="text-2xl font-bold text-gray-900 dark:text-white" id="kpi-vip-parking">0</dd>
            </div>
            
            <div class="glass-panel overflow-hidden rounded-xl p-4 shadow-sm border-l-4 border-l-purple-500">
                <dt class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Thời Gian Đỗ (TB)</dt>
                <dd class="text-2xl font-bold text-gray-900 dark:text-white" id="kpi-avg-time">0m</dd>
            </div>
            
            <div class="glass-panel overflow-hidden rounded-xl p-4 shadow-sm border-l-4 border-l-slate-400">
                <dt class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Số Vé Thanh Toán</dt>
                <dd class="text-2xl font-bold text-gray-900 dark:text-white" id="kpi-paid-count">0</dd>
            </div>
            
            <div class="glass-panel overflow-hidden rounded-xl p-4 shadow-sm border-l-4 border-l-emerald-500 bg-emerald-50/50 dark:bg-emerald-900/10">
                <dt class="text-xs font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider mb-1">Doanh Thu Thuần</dt>
                <dd class="text-2xl font-bold text-emerald-600 dark:text-emerald-400" id="kpi-total-revenue">0 đ</dd>
            </div>
        </div>

        <!-- 3 Biểu Đồ -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <!-- Xem lưu lượng qua giờ -->
            <div class="glass-panel rounded-2xl shadow-sm p-5 lg:col-span-2 relative min-h-[300px]">
                <div id="loading-chart-1" class="loading-overlay hidden rounded-2xl"><i class="fa-solid fa-spinner fa-spin text-brand-500 text-3xl"></i></div>
                <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3 uppercase tracking-wide">
                    Lưu lượng xe vào theo khung giờ
                </h3>
                <div class="h-64 relative w-full"><canvas id="hourlyTrafficChart"></canvas></div>
            </div>

            <!-- Cơ Cấu Khách Hàng -->
            <div class="glass-panel rounded-2xl shadow-sm p-5 relative min-h-[300px]">
                <div id="loading-chart-2" class="loading-overlay hidden rounded-2xl"><i class="fa-solid fa-spinner fa-spin text-brand-500 text-3xl"></i></div>
                <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3 uppercase tracking-wide">
                    Tỷ Lệ Tệp Khách Hàng
                </h3>
                <div class="h-64 relative w-full mt-2"><canvas id="ticketTypeChart"></canvas></div>
            </div>

            <!-- Xu Hướng -->
            <div class="glass-panel rounded-2xl shadow-sm p-5 lg:col-span-3 relative min-h-[300px]">
                <div id="loading-chart-3" class="loading-overlay hidden rounded-2xl"><i class="fa-solid fa-spinner fa-spin text-brand-500 text-3xl"></i></div>
                <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3 uppercase tracking-wide">
                    Xu Hướng Phương Tiện (7 Ngày)
                </h3>
                <div class="h-64 relative w-full"><canvas id="trendChart"></canvas></div>
            </div>
        </div>

        <!-- Grid 2 Bảng Data -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            <!-- Hoạt động gần đây -->
            <div class="glass-panel rounded-2xl shadow-sm p-5 flex flex-col">
                <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-4 uppercase tracking-wide flex justify-between">
                    <span><i class="fa-solid fa-clock-rotate-left mr-1.5 text-brand-500"></i> Sự kiện ra/vào gần nhất</span>
                </h3>
                <div class="overflow-x-auto flex-1">
                    <table class="w-full text-sm text-left">
                        <thead class="text-xs text-gray-500 bg-gray-50/50 dark:bg-gray-800/50 dark:text-gray-400 uppercase">
                            <tr>
                                <th class="px-4 py-2 rounded-l-lg">Biển Số</th>
                                <th class="px-4 py-2">Loại Thẻ</th>
                                <th class="px-4 py-2">Giờ Vào</th>
                                <th class="px-4 py-2 rounded-r-lg">Tình Trạng</th>
                            </tr>
                        </thead>
                        <tbody id="table-recent" class="divide-y divide-gray-100 dark:divide-gray-800">
                            <!-- JS Injection -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Top Xe đỗ lâu nhất -->
            <div class="glass-panel rounded-2xl shadow-sm p-5 flex flex-col">
                <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-4 uppercase tracking-wide flex justify-between border-b border-rose-100 dark:border-rose-900 pb-2">
                    <span class="text-rose-600 dark:text-rose-400"><i class="fa-solid fa-fire mr-1.5"></i> Vua Đỗ Lì (Top chi phí đỗ lâu)</span>
                </h3>
                <div class="overflow-x-auto flex-1">
                    <table class="w-full text-sm text-left">
                        <thead class="text-xs text-gray-500 bg-gray-50/50 dark:bg-gray-800/50 dark:text-gray-400 uppercase">
                            <tr>
                                <th class="px-4 py-2 rounded-l-lg">Top</th>
                                <th class="px-4 py-2">Biển Số</th>
                                <th class="px-4 py-2">Tổng Thời Gian</th>
                                <th class="px-4 py-2 rounded-r-lg">Tổng Bill</th>
                            </tr>
                        </thead>
                        <tbody id="table-longest" class="divide-y divide-gray-100 dark:divide-gray-800">
                            <!-- JS Injection -->
                        </tbody>
                    </table>
                </div>
            </div>

        </div>

    </main>

    <script>
        // Init dates mapping
        const dEnd = new Date();
        const dStart = new Date();
        dStart.setDate(dEnd.getDate() - 30);
        
        document.getElementById('start_date').value = dStart.toISOString().split('T')[0];
        document.getElementById('end_date').value = dEnd.toISOString().split('T')[0];

        // Dark/Light Mode logic (Premium Feel)
        const themeToggleBtn = document.getElementById('theme-toggle');
        const darkIcon = document.getElementById('theme-toggle-dark-icon');
        const lightIcon = document.getElementById('theme-toggle-light-icon');

        function getTheme() {
            if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) return 'dark';
            return 'light';
        }

        if (getTheme() === 'dark') { lightIcon.classList.remove('hidden'); } else { darkIcon.classList.remove('hidden'); }

        themeToggleBtn.addEventListener('click', function() {
            darkIcon.classList.toggle('hidden');
            lightIcon.classList.toggle('hidden');
            if (localStorage.getItem('color-theme')) {
                if (localStorage.getItem('color-theme') === 'light') { document.documentElement.classList.add('dark'); localStorage.setItem('color-theme', 'dark'); } 
                else { document.documentElement.classList.remove('dark'); localStorage.setItem('color-theme', 'light'); }
            } else {
                if (document.documentElement.classList.contains('dark')) { document.documentElement.classList.remove('dark'); localStorage.setItem('color-theme', 'light'); } 
                else { document.documentElement.classList.add('dark'); localStorage.setItem('color-theme', 'dark'); }
            }
            updateChartColors();
        });

        // ---------------- CHART.JS INIT ----------------
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.color = function() { return getTheme() === 'dark' ? '#94a3b8' : '#64748b'; }; 

        const ctx1 = document.getElementById('hourlyTrafficChart').getContext('2d');
        const hourlyChart = new Chart(ctx1, {
            type: 'bar',
            data: { labels: [], datasets: [{ label: 'Xe Vào', data: [], backgroundColor: 'rgba(14, 165, 233, 0.7)', borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, grid: { color: 'rgba(156, 163, 175, 0.1)' } }, x: { grid: { display: false } } } }
        });

        const ctx2 = document.getElementById('ticketTypeChart').getContext('2d');
        const typeChart = new Chart(ctx2, {
            type: 'doughnut',
            data: { labels: [], datasets: [{ data: [], backgroundColor: ['#0ea5e9', '#f59e0b'], borderWidth: 0, hoverOffset: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: '70%', plugins: { legend: { position: 'bottom' } } }
        });

        const ctx3 = document.getElementById('trendChart').getContext('2d');
        const trendChart = new Chart(ctx3, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Lượt Xe Trong Ngày', data: [], borderColor: '#f43f5e', backgroundColor: 'rgba(244, 63, 94, 0.1)', tension: 0.4, fill: true, pointBackgroundColor: '#f43f5e' }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: { y: { min: 0, grid: { color: 'rgba(156, 163, 175, 0.1)' } }, x: { grid: { display: false } } } }
        });

        function updateChartColors() {
            const gridColor = getTheme() === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';
            [hourlyChart, typeChart, trendChart].forEach(chart => {
                if (chart.options.scales?.y) chart.options.scales.y.grid.color = gridColor;
                if (chart.options.scales?.x) chart.options.scales.x.grid.color = gridColor;
                chart.update();
            });
            Chart.defaults.color = getTheme() === 'dark' ? '#94a3b8' : '#64748b';
        }
        updateChartColors();

        // ---------------- API FETCH LOGIC ----------------
        
        function resetFilters() {
            const dEnd = new Date();
            const dStart = new Date();
            dStart.setDate(dEnd.getDate() - 30);
            document.getElementById('start_date').value = dStart.toISOString().split('T')[0];
            document.getElementById('end_date').value = dEnd.toISOString().split('T')[0];
            loadData();
        }

        function exportData() {
            const s = document.getElementById('start_date').value;
            const e = document.getElementById('end_date').value;
            window.location.href = `/api/analytics/export?start_date=${s}&end_date=${e}`;
        }

        function loadData() {
            const s = document.getElementById('start_date').value;
            const e = document.getElementById('end_date').value;
            
            // Show loading overlays
            document.querySelectorAll('.loading-overlay').forEach(el => el.classList.remove('hidden'));
            
            fetch(`/api/analytics/dashboard_data?start_date=${s}&end_date=${e}`)
                .then(res => {
                    if (res.status === 403) {
                        alert("Bảo Vệ không được cấp quyền xem dữ liệu kinh doanh.");
                        throw new Error("Unauthorized");
                    }
                    return res.json()
                })
                .then(data => {
                    // Update KPIs
                    document.getElementById('kpi-total-visits').innerText = data.kpi.total_visits;
                    document.getElementById('kpi-total-parking').innerText = data.kpi.total_parking;
                    document.getElementById('kpi-vip-parking').innerText = data.kpi.vip_parking;
                    document.getElementById('kpi-avg-time').innerText = data.kpi.avg_time;
                    document.getElementById('kpi-paid-count').innerText = data.kpi.paid_count;
                    document.getElementById('kpi-total-revenue').innerText = data.kpi.total_revenue;

                    // Update Charts
                    hourlyChart.data.labels = data.charts.hourly.labels;
                    hourlyChart.data.datasets[0].data = data.charts.hourly.data;
                    hourlyChart.update();

                    typeChart.data.labels = data.charts.ticket_type.labels;
                    typeChart.data.datasets[0].data = data.charts.ticket_type.data;
                    typeChart.update();

                    trendChart.data.labels = data.charts.trend.labels;
                    trendChart.data.datasets[0].data = data.charts.trend.data;
                    trendChart.update();

                    // Update Tables
                    const trBody = document.getElementById('table-recent');
                    trBody.innerHTML = '';
                    if(data.tables.recent.length === 0) {
                        trBody.innerHTML = '<tr><td colspan="4" class="px-4 py-8 text-center text-gray-500">Chưa có dữ liệu</td></tr>';
                    } else {
                        data.tables.recent.forEach(row => {
                            let badge = row.status === 'PARKING' ? '<span class="text-[10px] bg-blue-100 text-blue-800 px-2 flex items-center h-5 w-fit rounded-full dark:bg-blue-900/50 dark:text-blue-300">ĐANG GỬI</span>' : 
                                        (row.status === 'COMPLETED' ? '<span class="text-[10px] bg-gray-100 text-gray-600 px-2 flex items-center h-5 w-fit rounded-full dark:bg-gray-800 dark:text-gray-400">RA BÃI</span>' : 
                                        '<span class="text-[10px] bg-red-100 text-red-600 px-2 flex items-center h-5 w-fit rounded-full dark:bg-red-900/50 dark:text-red-300">HUỶ</span>');
                                        
                            trBody.innerHTML += `
                            <tr class="hover:bg-gray-50 dark:hover:bg-gray-800/80 transition group">
                                <td class="px-4 py-2 font-mono font-medium text-brand-600 dark:text-brand-400 opacity-90 group-hover:opacity-100">${row.license_plate}</td>
                                <td class="px-4 py-2 text-xs text-gray-600 dark:text-gray-300">${row.type}</td>
                                <td class="px-4 py-2 text-xs text-gray-600 dark:text-gray-300">${row.time_in}</td>
                                <td class="px-4 py-2">${badge}</td>
                            </tr>`;
                        });
                    }

                    const tlBody = document.getElementById('table-longest');
                    tlBody.innerHTML = '';
                    if(data.tables.longest.length === 0) {
                        tlBody.innerHTML = '<tr><td colspan="4" class="px-4 py-8 text-center text-gray-500">Chưa có dữ liệu thanh toán</td></tr>';
                    } else {
                        data.tables.longest.forEach(row => {
                            let crown = row.rank <= 3 ? `<i class="fa-solid fa-medal text-${row.rank==1?'yellow':(row.rank==2?'slate':'amber')}-500 mr-1 shadow-sm"></i>` : `<span class="text-gray-400 ml-1">#</span>`;
                            tlBody.innerHTML += `
                            <tr class="hover:bg-rose-50/50 dark:hover:bg-rose-900/10 transition group">
                                <td class="px-4 py-2 font-bold opacity-80">${crown}${row.rank}</td>
                                <td class="px-4 py-2 font-mono font-medium text-gray-800 dark:text-gray-200">${row.license_plate}</td>
                                <td class="px-4 py-2 text-xs text-rose-600 dark:text-rose-400 font-medium">${row.duration}</td>
                                <td class="px-4 py-2 text-xs font-bold text-gray-600 dark:text-gray-300 group-hover:text-emerald-500 transition">${row.fee}</td>
                            </tr>`;
                        });
                    }
                    
                    document.querySelectorAll('.loading-overlay').forEach(el => el.classList.add('hidden'));
                })
                .catch(err => {
                    console.error("Lỗi tải Analytics API", err);
                    document.querySelectorAll('.loading-overlay').forEach(el => el.classList.add('hidden'));
                });
        }

        // Init load
        document.addEventListener("DOMContentLoaded", () => {
            loadData();
        });

    </script>
</body>
</html>
{% endblock %}
"""

with open('templates/analytics.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated successfully")
