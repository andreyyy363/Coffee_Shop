function initForecast(config) {
    // ── API URL ──
    const API_URL = config.apiUrl;

    // ── DOM refs ──
    const paramMetric = document.getElementById('paramMetric');
    const paramDaysBack = document.getElementById('paramDaysBack');
    const paramForecastDays = document.getElementById('paramForecastDays');
    const paramAlpha = document.getElementById('paramAlpha');
    const paramBeta = document.getElementById('paramBeta');
    const paramGamma = document.getElementById('paramGamma');
    const alphaLabel = document.getElementById('alphaValue');
    const betaLabel = document.getElementById('betaValue');
    const gammaLabel = document.getElementById('gammaValue');
    const loadingEl = document.getElementById('loadingIndicator');
    const forecastForm = document.getElementById('forecastForm');

    // ── Chart instances ──
    let forecastChart = null;
    let topProductsChart = null;

    // ── Helpers ──
    const formatDate = (d) => {
        const dt = new Date(d);
        return dt.toLocaleDateString('en-US', {month: 'short', day: 'numeric'});
    };

    const CHART_COLORS = [
        '#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#dc3545',
        '#fd7e14', '#ffc107', '#198754', '#20c997', '#0dcaf0'
    ];

    // ── Build / update main chart ──
    function buildForecastChart(data, metric) {
        const ctx = document.getElementById('forecastChart');
        if (!ctx) return;

        const metricLabel = metric === 'revenue' ? 'Revenue (USD)' : 'Order Count';
        const allDates = [...data.dates, ...data.forecast_dates];

        const actualData = [...data.actual, ...Array(data.forecast_dates.length).fill(null)];
        const hwSmoothedData = [...data.hw_smoothed, ...Array(data.forecast_dates.length).fill(null)];
        const maSmoothedData = [...data.ma_smoothed, ...Array(data.forecast_dates.length).fill(null)];
        const hwForecastData = [
            ...Array(data.dates.length - 1).fill(null),
            data.hw_smoothed[data.hw_smoothed.length - 1],
            ...data.hw_forecast
        ];
        const maForecastData = [
            ...Array(data.dates.length - 1).fill(null),
            data.ma_smoothed[data.ma_smoothed.length - 1],
            ...data.ma_forecast
        ];

        // Store divider index for plugin
        const dividerIndex = data.dates.length - 1;

        const chartData = {
            labels: allDates.map(formatDate),
            datasets: [
                {
                    label: 'Actual ' + metricLabel,
                    data: actualData,
                    borderColor: 'rgba(108, 117, 125, 0.5)',
                    backgroundColor: 'rgba(108, 117, 125, 0.05)',
                    borderWidth: 1, pointRadius: 0, fill: true, order: 4,
                },
                {
                    label: 'Holt-Winters Smoothed',
                    data: hwSmoothedData,
                    borderColor: '#0d6efd',
                    borderWidth: 2, pointRadius: 0, order: 2,
                },
                {
                    label: 'Moving Average (7d)',
                    data: maSmoothedData,
                    borderColor: '#6f42c1',
                    borderWidth: 1.5, borderDash: [4, 4], pointRadius: 0, order: 3,
                },
                {
                    label: 'HW Forecast',
                    data: hwForecastData,
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.08)',
                    borderWidth: 2.5, borderDash: [6, 3], pointRadius: 0, fill: true, order: 1,
                },
                {
                    label: 'MA Forecast',
                    data: maForecastData,
                    borderColor: '#6f42c1',
                    borderWidth: 1.5, borderDash: [2, 4], pointRadius: 0, order: 3,
                },
            ],
        };

        const chartOptions = {
            responsive: true,
            animation: {duration: 400},
            interaction: {mode: 'index', intersect: false},
            plugins: {legend: {position: 'top'}},
            scales: {
                x: {
                    display: true,
                    ticks: {maxTicksAllowed: 20, maxRotation: 45, autoSkip: true, autoSkipPadding: 10},
                    grid: {display: false},
                },
                y: {
                    beginAtZero: true,
                    title: {display: true, text: metricLabel},
                },
            },
        };

        const dividerPlugin = {
            id: 'forecastDivider',
            beforeDraw(chart) {
                const xScale = chart.scales.x;
                const yScale = chart.scales.y;
                const x = xScale.getPixelForValue(dividerIndex);
                const c = chart.ctx;
                c.save();
                c.beginPath();
                c.setLineDash([5, 5]);
                c.strokeStyle = 'rgba(220, 53, 69, 0.4)';
                c.lineWidth = 1;
                c.moveTo(x, yScale.top);
                c.lineTo(x, yScale.bottom);
                c.stroke();
                c.fillStyle = 'rgba(220, 53, 69, 0.7)';
                c.font = '11px sans-serif';
                c.textAlign = 'center';
                c.fillText('Forecast →', x + 35, yScale.top + 12);
                c.restore();
            }
        };

        if (forecastChart) {
            forecastChart.data = chartData;
            forecastChart.options = chartOptions;
            forecastChart.config.plugins = [dividerPlugin];
            forecastChart.update();
        } else {
            forecastChart = new Chart(ctx, {
                type: 'line',
                data: chartData,
                options: chartOptions,
                plugins: [dividerPlugin],
            });
        }
    }

    // ── Build / update top products chart ──
    function buildTopProductsChart(products, metric) {
        const ctx = document.getElementById('topProductsChart');
        if (!ctx) return;
        const section = document.getElementById('topProductsSection');

        if (!products || products.length === 0) {
            if (section) section.style.display = 'none';
            return;
        }
        if (section) section.style.display = '';

        const names = products.map(p => p.product_name.length > 20 ? p.product_name.substring(0, 20) + '...' : p.product_name);
        const revenues = products.map(p => p.total_revenue);
        const label = metric === 'revenue' ? 'Revenue (USD)' : 'Qty Sold';
        const vals = metric === 'revenue' ? revenues : products.map(p => p.total_qty);

        const chartData = {
            labels: names,
            datasets: [{
                label: label,
                data: vals,
                backgroundColor: CHART_COLORS,
                borderRadius: 4,
            }],
        };
        const chartOptions = {
            indexAxis: 'y',
            responsive: true,
            animation: {duration: 400},
            plugins: {legend: {display: false}},
            scales: {
                x: {beginAtZero: true, title: {display: true, text: label}},
                y: {ticks: {font: {size: 11}}},
            },
        };

        if (topProductsChart) {
            topProductsChart.data = chartData;
            topProductsChart.options = chartOptions;
            topProductsChart.update();
        } else {
            topProductsChart = new Chart(ctx, {type: 'bar', data: chartData, options: chartOptions});
        }
    }

    // ── Update summary cards ──
    function updateSummary(result, metric, daysBack, forecastDays) {
        const s = result.summary;
        const noData = !s || s === 'No sales data available.';
        const dataSection = document.getElementById('summaryCards');
        const noDataCard = document.getElementById('noDataCard');

        if (noData) {
            if (dataSection) dataSection.style.display = 'none';
            if (noDataCard) noDataCard.style.display = '';
            document.querySelector('.card .card-body canvas#forecastChart')?.closest('.card')?.style.setProperty('display', 'none');
            return;
        }

        if (dataSection) dataSection.style.display = '';
        if (noDataCard) noDataCard.style.display = 'none';

        const prefix = metric === 'revenue' ? '$' : '';
        const suffix = metric === 'revenue' ? '' : ' orders';
        document.getElementById('summaryDays').textContent = daysBack;
        document.getElementById('summaryTotal').textContent = prefix + s.total_revenue + suffix;
        document.getElementById('summaryAvg').textContent = prefix + s.avg_daily + suffix;
        document.getElementById('summaryFcDays').textContent = forecastDays;
        document.getElementById('summaryForecast').textContent = prefix + s.forecast_total + suffix;

        const trendEl = document.getElementById('summaryTrend');
        if (s.trend === 'up') {
            trendEl.innerHTML = '<span class="text-success"><i class="bi bi-arrow-up-circle"></i> Growing</span>';
        } else if (s.trend === 'down') {
            trendEl.innerHTML = '<span class="text-danger"><i class="bi bi-arrow-down-circle"></i> Declining</span>';
        } else {
            trendEl.innerHTML = '<span class="text-warning"><i class="bi bi-dash-circle"></i> Stable</span>';
        }
    }

    // ── Update chart title ──
    function updateChartTitle(metric) {
        const el = document.getElementById('chartTitle');
        if (el) {
            el.innerHTML = '<i class="bi bi-graph-up me-2"></i>' +
                (metric === 'revenue' ? 'Revenue' : 'Orders') + ' — History & Forecast';
        }
    }

    // ── Update error metrics table ──
    function updateMetricsTable(metrics) {
        if (!metrics) return;
        const ma = metrics.moving_average;
        const hw = metrics.holt_winters;

        const badge = (hwVal, maVal) =>
            parseFloat(hwVal) < parseFloat(maVal) ? ' <span class="badge bg-success ms-1">Better</span>' : '';

        document.getElementById('maMae').textContent = ma.mae;
        document.getElementById('hwMae').innerHTML = '<strong>' + hw.mae + '</strong>' + badge(hw.mae, ma.mae);
        document.getElementById('maRmse').textContent = ma.rmse;
        document.getElementById('hwRmse').innerHTML = '<strong>' + hw.rmse + '</strong>' + badge(hw.rmse, ma.rmse);
        document.getElementById('maMape').textContent = ma.mape + '%';
        document.getElementById('hwMape').innerHTML = '<strong>' + hw.mape + '%</strong>' + badge(hw.mape, ma.mape);
    }

    // ── Update model badges ──
    function updateModelBadges(alpha, beta, gamma) {
        const el = document.getElementById('modelBadges');
        if (el) {
            el.innerHTML =
                '<span class="badge bg-secondary">α = ' + alpha + '</span> ' +
                '<span class="badge bg-secondary">β = ' + beta + '</span> ' +
                '<span class="badge bg-secondary">γ = ' + gamma + '</span>';
        }
    }

    // ── Update top products table ──
    function updateTopProductsTable(products, daysBack) {
        document.getElementById('topProductsDays').textContent = daysBack;
        const tbody = document.getElementById('topProductsBody');
        if (!tbody) return;
        tbody.innerHTML = products.map((p, i) =>
            `<tr><td>${i + 1}</td><td>${p.product_name}</td><td>${p.total_qty}</td><td>$${p.total_revenue}</td></tr>`
        ).join('');
    }

    // ── AJAX fetch ──
    let fetchController = null;

    function fetchForecast() {
        if (fetchController) fetchController.abort();
        fetchController = new AbortController();

        const params = new URLSearchParams({
            metric: paramMetric.value,
            days_back: paramDaysBack.value,
            forecast_days: paramForecastDays.value,
            alpha: paramAlpha.value,
            beta: paramBeta.value,
            gamma: paramGamma.value,
        });

        loadingEl.classList.remove('d-none');

        fetch(API_URL + '?' + params.toString(), {
            signal: fetchController.signal,
            headers: {'X-Requested-With': 'XMLHttpRequest'},
        })
            .then(resp => resp.json())
            .then(data => {
                loadingEl.classList.add('d-none');
                const result = data.result;
                const metric = data.metric;

                updateSummary(result, metric, data.days_back, data.forecast_days);
                updateChartTitle(metric);
                buildForecastChart(result, metric);
                updateMetricsTable(result.metrics);
                updateModelBadges(data.alpha, data.beta, data.gamma);
                updateTopProductsTable(data.top_products, data.days_back);
                buildTopProductsChart(data.top_products, metric);

                // Update URL without reload
                const url = new URL(window.location);
                url.search = params.toString();
                history.replaceState(null, '', url);
            })
            .catch(err => {
                if (err.name !== 'AbortError') {
                    loadingEl.classList.add('d-none');
                    console.error('Forecast fetch error:', err);
                }
            });
    }

    // ── Debounce ──
    let debounceTimer = null;

    function debouncedFetch(delay) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(fetchForecast, delay);
    }

    // ── Slider label sync + trigger fetch ──
    paramAlpha.addEventListener('input', () => {
        alphaLabel.textContent = paramAlpha.value;
        debouncedFetch(200);
    });
    paramBeta.addEventListener('input', () => {
        betaLabel.textContent = paramBeta.value;
        debouncedFetch(200);
    });
    paramGamma.addEventListener('input', () => {
        gammaLabel.textContent = paramGamma.value;
        debouncedFetch(200);
    });

    // ── Other controls trigger fetch ──
    paramMetric.addEventListener('change', () => debouncedFetch(100));
    paramDaysBack.addEventListener('change', () => debouncedFetch(300));
    paramForecastDays.addEventListener('change', () => debouncedFetch(300));

    // Prevent form submit (no page reload)
    forecastForm.addEventListener('submit', (e) => {
        e.preventDefault();
        fetchForecast();
    });

    // ── Initial render from server data ──
    if (config.initialData) {
        buildForecastChart(config.initialData, config.metric);
    }
    if (config.topProducts) {
        buildTopProductsChart(config.topProducts, config.metric);
    }
}
