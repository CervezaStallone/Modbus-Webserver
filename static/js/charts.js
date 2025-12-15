/**
 * Chart.js configuration and utilities
 */

/**
 * Create a line chart for trend data
 */
function createLineChart(canvasId, config) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element ${canvasId} not found`);
        return null;
    }
    
    const defaultConfig = {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: config.label || 'Value',
                data: [],
                borderColor: config.color || '#007bff',
                backgroundColor: config.color ? config.color + '20' : '#007bff20',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: config.showLegend !== false
                },
                title: {
                    display: !!config.title,
                    text: config.title
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    min: config.yMin,
                    max: config.yMax
                },
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute'
                    }
                }
            }
        }
    };
    
    return new Chart(ctx, defaultConfig);
}

/**
 * Update chart with new data point
 */
function updateChart(chart, timestamp, value, maxDataPoints = 100) {
    if (!chart) return;
    
    chart.data.labels.push(timestamp);
    chart.data.datasets[0].data.push(value);
    
    // Remove old data points
    if (chart.data.labels.length > maxDataPoints) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
    }
    
    chart.update('none'); // Update without animation for performance
}

/**
 * Create a gauge chart
 */
function createGaugeChart(canvasId, config) {
    // Gauge implementation using Chart.js doughnut
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [config.value || 0, config.max - (config.value || 0)],
                backgroundColor: [
                    config.color || '#007bff',
                    '#e9ecef'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            circumference: 180,
            rotation: -90,
            cutout: '70%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: false
                }
            }
        }
    });
}

/**
 * Update gauge chart value
 */
function updateGauge(chart, value, max) {
    if (!chart) return;
    
    chart.data.datasets[0].data = [value, max - value];
    chart.update();
}
