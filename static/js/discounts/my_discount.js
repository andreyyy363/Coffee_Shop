function initDiscountCurveChart() {
	if (typeof Chart === 'undefined') {
		return;
	}

	const canvas = document.getElementById('discountCurve');
	if (!canvas || !Array.isArray(window.curveData)) {
		return;
	}

	const curvePoints = window.curveData.map(point => ({
		x: point.rfm_score,
		y: point.discount_percent,
	}));

	const datasets = [
		{
			label: 'Discount %',
			data: curvePoints,
			borderColor: '#c0976c',
			backgroundColor: 'rgba(192, 151, 108, 0.1)',
			fill: true,
			tension: 0.35,
			pointRadius: 0,
			borderWidth: 2,
			order: 1,
		}
	];

	const ctx = canvas.getContext('2d');
	const currentPoint = (typeof window.currentRfm !== 'undefined' && typeof window.currentDiscount !== 'undefined')
		? {x: window.currentRfm, y: window.currentDiscount}
		: null;
	const pointOverlay = {
		id: 'currentPointOverlay',
		afterDraw(chart) {
			if (!currentPoint) {
				return;
			}

			const x = chart.scales.x.getPixelForValue(currentPoint.x);
			const y = chart.scales.y.getPixelForValue(currentPoint.y);
			const ctx = chart.ctx;
			ctx.save();
			ctx.beginPath();
			ctx.arc(x, y, 6, 0, Math.PI * 2);
			ctx.fillStyle = '#0d6efd';
			ctx.fill();
			ctx.lineWidth = 2;
			ctx.strokeStyle = '#ffffff';
			ctx.stroke();
			ctx.restore();
		}
	};
	new Chart(ctx, {
		type: 'line',
		data: {datasets},
		plugins: [pointOverlay],
		options: {
			responsive: true,
			plugins: {
				legend: {display: false},
				tooltip: {
					callbacks: {
						label: function (context) {
							if (context.parsed && typeof context.parsed.y !== 'undefined') {
								return context.parsed.y + '%';
							}
							return '';
						}
					}
				}
			},
			scales: {
				x: {
					type: 'linear',
					min: 0,
					max: 1,
					title: {display: true, text: 'RFM Score'},
					ticks: {maxTicksLimit: 6}
				},
				y: {
					title: {display: true, text: 'Discount %'},
					beginAtZero: true
				}
			}
		}
	});
}

if (document.readyState === 'loading') {
	document.addEventListener('DOMContentLoaded', initDiscountCurveChart);
} else {
	initDiscountCurveChart();
}
