function initInventoryForecast(config) {
    const API_URL = config.apiUrl;
    const PRODUCT_API_URL = config.productApiUrl;

    // ── DOM refs ──
    const paramDaysBack = document.getElementById('paramDaysBack');
    const paramForecastDays = document.getElementById('paramForecastDays');
    const paramLeadTime = document.getElementById('paramLeadTime');
    const paramServiceLevel = document.getElementById('paramServiceLevel');
    const paramAlpha = document.getElementById('paramAlpha');
    const paramBeta = document.getElementById('paramBeta');
    const paramGamma = document.getElementById('paramGamma');
    const alphaLabel = document.getElementById('alphaValue');
    const betaLabel = document.getElementById('betaValue');
    const gammaLabel = document.getElementById('gammaValue');
    const loadingEl = document.getElementById('loadingIndicator');
    const inventoryForm = document.getElementById('inventoryForm');

    let inventoryChart = null;
    let productDemandChart = null;

    const COLORS = {
        primary: '#0d6efd',
        success: '#198754',
        danger: '#dc3545',
        warning: '#ffc107',
        info: '#0dcaf0',
        purple: '#6f42c1',
    };

    const formatDate = (d) => {
        const dt = new Date(d);
        return dt.toLocaleDateString('en-US', {month: 'short', day: 'numeric'});
    };

    // ── Build inventory overview chart ──
    function buildInventoryChart(products) {
        const ctx = document.getElementById('inventoryChart');
        if (!ctx || !products || products.length === 0) return;

        const top = products.slice(0, 15);
        const names = top.map(p => p.product_name.length > 25 ? p.product_name.substring(0, 25) + '...' : p.product_name);

        const chartData = {
            labels: names,
            datasets: [
                {
                    label: 'Forecasted Demand',
                    data: top.map(p => p.forecast_total),
                    backgroundColor: 'rgba(13, 110, 253, 0.6)',
                    borderRadius: 4,
                    order: 2,
                },
                {
                    label: 'Safety Stock',
                    data: top.map(p => p.safety_stock),
                    backgroundColor: 'rgba(255, 193, 7, 0.7)',
                    borderRadius: 4,
                    order: 1,
                },
                {
                    label: 'Recommended Order Qty',
                    data: top.map(p => p.recommended_order_qty),
                    type: 'line',
                    borderColor: COLORS.danger,
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 4,
                    pointBackgroundColor: COLORS.danger,
                    order: 0,
                },
            ],
        };

        const chartOptions = {
            responsive: true,
            animation: {duration: 400},
            plugins: {
                legend: {position: 'top'},
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            return ctx.dataset.label + ': ' + ctx.parsed.y + ' units';
                        }
                    }
                }
            },
            scales: {
                x: {ticks: {font: {size: 11}, maxRotation: 45}},
                y: {beginAtZero: true, title: {display: true, text: 'Units'}},
            },
        };

        if (inventoryChart) {
            inventoryChart.data = chartData;
            inventoryChart.options = chartOptions;
            inventoryChart.update();
        } else {
            inventoryChart = new Chart(ctx, {type: 'bar', data: chartData, options: chartOptions});
        }
    }

    // ── Update summary cards ──
    function updateSummary(summary) {
        if (!summary) return;
        const el = (id) => document.getElementById(id);
        if (el('summaryProducts')) el('summaryProducts').textContent = summary.total_products;
        if (el('summaryTotalUnits')) el('summaryTotalUnits').textContent = summary.total_recommended_units;
        if (el('summaryGrowing')) el('summaryGrowing').innerHTML = '<i class="bi bi-arrow-up-circle"></i> ' + summary.growing_products;
        if (el('summaryDeclining')) el('summaryDeclining').innerHTML = '<i class="bi bi-arrow-down-circle"></i> ' + summary.declining_products;
        if (el('summaryStable')) el('summaryStable').innerHTML = '<i class="bi bi-dash-circle"></i> ' + summary.stable_products;
        if (el('summaryAvgSafety')) el('summaryAvgSafety').textContent = summary.avg_safety_stock;
    }

    // ── Update products table ──
    function updateProductsTable(products) {
        const tbody = document.getElementById('productsTableBody');
        if (!tbody) return;

        tbody.innerHTML = products.map((p, i) => {
            const trendBadge = p.trend === 'growing'
                ? '<span class="badge bg-success"><i class="bi bi-arrow-up"></i> Growing</span>'
                : p.trend === 'declining'
                    ? '<span class="badge bg-danger"><i class="bi bi-arrow-down"></i> Declining</span>'
                    : '<span class="badge bg-warning text-dark"><i class="bi bi-dash"></i> Stable</span>';

            const patternBadge = p.demand_pattern === 'stable'
                ? `<span class="badge bg-info text-dark">Stable (CV=${p.cv})</span>`
                : p.demand_pattern === 'variable'
                    ? `<span class="badge bg-warning text-dark">Variable (CV=${p.cv})</span>`
                    : `<span class="badge bg-danger">Highly Variable (CV=${p.cv})</span>`;

            return `<tr data-product-id="${p.product_id}" data-sold="${p.total_sold}" data-order="${p.recommended_order_qty}" data-safety="${p.safety_stock}">
        <td>${i + 1}</td>
        <td><strong>${p.product_name}</strong></td>
        <td>${p.total_sold}</td>
        <td>${p.avg_daily_demand}</td>
        <td>${trendBadge}</td>
        <td>${patternBadge}</td>
        <td>${p.forecast_total} units</td>
        <td><strong>${p.safety_stock}</strong></td>
        <td>${p.reorder_point}</td>
        <td><span class="badge bg-primary fs-6">${p.recommended_order_qty}</span></td>
        <td><button class="btn btn-sm btn-outline-primary btn-detail" data-product-id="${p.product_id}" title="View demand chart"><i class="bi bi-graph-up"></i></button></td>
    </tr>`;
        }).join('');

        // Re-attach detail button handlers
        attachDetailHandlers();
    }

    // ── Update model badges ──
    function updateModelBadges(params) {
        const el = document.getElementById('modelBadges');
        if (!el || !params) return;
        el.innerHTML =
            `<span class="badge bg-secondary">α = ${params.alpha}</span> ` +
            `<span class="badge bg-secondary">β = ${params.beta}</span> ` +
            `<span class="badge bg-secondary">γ = ${params.gamma}</span> ` +
            `<span class="badge bg-secondary">Lead Time = ${params.lead_time}d</span> ` +
            `<span class="badge bg-secondary">Service Level = ${params.service_level}%</span> ` +
            `<span class="badge bg-secondary">Z = ${params.z_score}</span>`;
    }

    // ── Product detail modal ──
    function showProductDetail(productId) {
        const params = new URLSearchParams({
            days_back: paramDaysBack.value,
            forecast_days: paramForecastDays.value,
            lead_time: paramLeadTime.value,
            service_level: paramServiceLevel.value,
            alpha: paramAlpha.value,
            beta: paramBeta.value,
            gamma: paramGamma.value,
        });

        const url = PRODUCT_API_URL.replace('{id}', productId) + '?' + params.toString();

        fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}})
            .then(r => r.json())
            .then(data => {
                if (data.error) return;

                document.getElementById('modalProductName').textContent = data.product_name + ' — Demand Forecast';
                document.getElementById('modalAvgDaily').textContent = data.avg_daily_demand + ' /day';
                document.getElementById('modalSafetyStock').textContent = data.safety_stock + ' units';
                document.getElementById('modalReorderPoint').textContent = data.reorder_point + ' units';
                document.getElementById('modalOrderQty').textContent = data.recommended_order_qty + ' units';

                const methodText = data.forecast_method === 'holt_winters'
                    ? 'Holt-Winters Triple Exponential Smoothing'
                    : data.forecast_method === 'moving_average'
                        ? 'Moving Average (fallback — insufficient data for HW)'
                        : 'No data';

                const metricsText = data.forecast_metrics
                    ? ` | MAE: ${data.forecast_metrics.mae}, RMSE: ${data.forecast_metrics.rmse}, MAPE: ${data.forecast_metrics.mape}%`
                    : '';

                document.getElementById('modalMethodInfo').textContent =
                    'Method: ' + methodText + metricsText +
                    ` | σ = ${data.demand_std}, CV = ${data.cv}`;

                buildProductDemandChart(data);

                const modal = new bootstrap.Modal(document.getElementById('productDetailModal'));
                modal.show();
            })
            .catch(err => console.error('Detail fetch error:', err));
    }

    function buildProductDemandChart(data) {
        const ctx = document.getElementById('productDemandChart');
        if (!ctx) return;

        const allDates = [...data.dates, ...data.forecast_dates];
        const actualData = [...data.history, ...Array(data.forecast_dates.length).fill(null)];

        let smoothedData = [];
        if (data.smoothed && data.smoothed.length > 0) {
            smoothedData = [...data.smoothed, ...Array(data.forecast_dates.length).fill(null)];
        }

        const forecastData = [
            ...Array(data.dates.length - 1).fill(null),
            data.history[data.history.length - 1],
            ...data.forecast,
        ];

        // Reorder point line
        const ropLine = Array(allDates.length).fill(data.reorder_point);
        // Safety stock line
        const ssLine = Array(allDates.length).fill(data.safety_stock);

        const dividerIndex = data.dates.length - 1;

        const datasets = [
            {
                label: 'Actual Demand',
                data: actualData,
                borderColor: 'rgba(108, 117, 125, 0.5)',
                backgroundColor: 'rgba(108, 117, 125, 0.05)',
                borderWidth: 1, pointRadius: 0, fill: true, order: 4,
            },
            {
                label: 'Forecasted Demand',
                data: forecastData,
                borderColor: COLORS.danger,
                backgroundColor: 'rgba(220, 53, 69, 0.08)',
                borderWidth: 2.5, borderDash: [6, 3], pointRadius: 0, fill: true, order: 1,
            },
            {
                label: 'Reorder Point (ROP)',
                data: ropLine,
                borderColor: COLORS.warning,
                borderWidth: 1.5, borderDash: [8, 4], pointRadius: 0, order: 0,
            },
            {
                label: 'Safety Stock (SS)',
                data: ssLine,
                borderColor: COLORS.info,
                borderWidth: 1, borderDash: [4, 4], pointRadius: 0, order: 0,
            },
        ];

        if (smoothedData.length > 0) {
            datasets.splice(1, 0, {
                label: 'Smoothed (HW)',
                data: smoothedData,
                borderColor: COLORS.primary,
                borderWidth: 2, pointRadius: 0, order: 2,
            });
        }

        const chartData = {labels: allDates.map(formatDate), datasets: datasets};
        const chartOptions = {
            responsive: true,
            animation: {duration: 400},
            interaction: {mode: 'index', intersect: false},
            plugins: {legend: {position: 'top'}},
            scales: {
                x: {ticks: {maxTicksAllowed: 20, maxRotation: 45, autoSkip: true}, grid: {display: false}},
                y: {beginAtZero: true, title: {display: true, text: 'Units / Day'}},
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

        if (productDemandChart) {
            productDemandChart.data = chartData;
            productDemandChart.options = chartOptions;
            productDemandChart.config.plugins = [dividerPlugin];
            productDemandChart.update();
        } else {
            productDemandChart = new Chart(ctx, {
                type: 'line', data: chartData, options: chartOptions, plugins: [dividerPlugin],
            });
        }
    }

    // ── Detail button handlers ──
    function attachDetailHandlers() {
        document.querySelectorAll('.btn-detail').forEach(btn => {
            btn.addEventListener('click', function () {
                showProductDetail(this.dataset.productId);
            });
        });
    }

    // ── Sorting ──
    function sortTable(field) {
        const tbody = document.getElementById('productsTableBody');
        if (!tbody) return;
        const rows = Array.from(tbody.querySelectorAll('tr'));
        rows.sort((a, b) => parseFloat(b.dataset[field]) - parseFloat(a.dataset[field]));
        rows.forEach((row, i) => {
            row.querySelector('td').textContent = i + 1;
            tbody.appendChild(row);
        });
    }

    document.querySelectorAll('[data-sort]').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('[data-sort]').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            sortTable(this.dataset.sort);
        });
    });

    // ── AJAX fetch ──
    let fetchController = null;

    function fetchInventory() {
        if (fetchController) fetchController.abort();
        fetchController = new AbortController();

        const params = new URLSearchParams({
            days_back: paramDaysBack.value,
            forecast_days: paramForecastDays.value,
            lead_time: paramLeadTime.value,
            service_level: paramServiceLevel.value,
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
                updateSummary(data.summary);
                updateProductsTable(data.products);
                buildInventoryChart(data.products);
                updateModelBadges(data.params);

                // Update URL
                const url = new URL(window.location);
                url.search = params.toString();
                history.replaceState(null, '', url);
            })
            .catch(err => {
                if (err.name !== 'AbortError') {
                    loadingEl.classList.add('d-none');
                    console.error('Inventory fetch error:', err);
                }
            });
    }

    // ── Debounce ──
    let debounceTimer = null;

    function debouncedFetch(delay) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(fetchInventory, delay);
    }

    // ── Control event listeners ──
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
    paramDaysBack.addEventListener('change', () => debouncedFetch(300));
    paramForecastDays.addEventListener('change', () => debouncedFetch(300));
    paramLeadTime.addEventListener('change', () => debouncedFetch(300));
    paramServiceLevel.addEventListener('change', () => debouncedFetch(300));

    inventoryForm.addEventListener('submit', (e) => {
        e.preventDefault();
        fetchInventory();
    });

    // ── Initial render ──
    attachDetailHandlers();

    if (config.initialProducts) {
        buildInventoryChart(config.initialProducts);
    }
}
