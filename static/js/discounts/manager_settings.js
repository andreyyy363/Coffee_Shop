/**
 * Discount curve chart for manager settings page.
 */
function initManagerSettingsChart(curveData) {
    const ctx = document.getElementById('discountCurve').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: curveData.map(d => d.rfm_score.toFixed(2)),
            datasets: [{
                label: 'Discount %',
                data: curveData.map(d => d.discount_percent),
                borderColor: '#c0976c',
                backgroundColor: 'rgba(192, 151, 108, 0.1)',
                fill: true,
                tension: 0.4,
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    title: {display: true, text: 'RFM Score'},
                    ticks: {maxTicksLimit: 6}
                },
                y: {
                    title: {display: true, text: 'Discount %'},
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {display: false}
            }
        }
    });
}
