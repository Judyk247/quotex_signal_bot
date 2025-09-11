// dashboard/static/js/dashboard.js
class TradingDashboard {
    constructor() {
        this.socket = io();
        this.performanceChart = null;
        this.distributionChart = null;
        this.signals = [];
        this.performanceData = {
            total_signals: 0,
            winning_signals: 0,
            losing_signals: 0,
            total_profit: 0
        };
        
        this.init();
    }

    init() {
        this.initializeCharts();
        this.setupSocketListeners();
        this.loadInitialData();
        this.setupEventListeners();
        
        // Update timestamp every minute
        setInterval(() => {
            this.updateLastUpdateTime();
        }, 60000);
    }

    initializeCharts() {
        // Performance Chart
        const performanceCtx = document.getElementById('performance-chart').getContext('2d');
        this.performanceChart = new Chart(performanceCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Account Balance',
                    data: [],
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#27ae60',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Performance Trend',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });

        // Distribution Chart
        const distributionCtx = document.getElementById('distribution-chart').getContext('2d');
        this.distributionChart = new Chart(distributionCtx, {
            type: 'doughnut',
            data: {
                labels: ['BUY Signals', 'SELL Signals'],
                datasets: [{
                    data: [0, 0],
                    backgroundColor: ['#27ae60', '#e74c3c'],
                    borderColor: ['#ffffff', '#ffffff'],
                    borderWidth: 2,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    title: {
                        display: true,
                        text: 'Signal Distribution',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    }
                }
            }
        });
    }

    setupSocketListeners() {
        // Performance updates
        this.socket.on('performance_update', (data) => {
            this.performanceData = data;
            this.updatePerformanceStats();
            this.updateCharts();
        });

        // New signals
        this.socket.on('new_signal', (signal) => {
            this.addSignalToUI(signal);
            this.showNotification(`New ${signal.direction} signal for ${signal.asset}`);
        });

        // Connection status
        this.socket.on('connect', () => {
            this.updateConnectionStatus('Online', 'status-online');
            this.socket.emit('clients_update');
        });

        this.socket.on('disconnect', () => {
            this.updateConnectionStatus('Offline', 'status-offline');
        });

        this.socket.on('clients_update', (count) => {
            document.getElementById('clients').textContent = count;
        });
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadInitialData();
        });

        // Filter signals
        document.getElementById('filter-asset').addEventListener('change', (e) => {
            this.filterSignals(e.target.value);
        });

        // Search functionality
        document.getElementById('search-signals').addEventListener('input', (e) => {
            this.searchSignals(e.target.value);
        });
    }

    async loadInitialData() {
        try {
            // Load signals
            const signalsResponse = await fetch('/api/signals');
            this.signals = await signalsResponse.json();
            this.displaySignals(this.signals);

            // Load performance data
            const performanceResponse = await fetch('/api/performance');
            this.performanceData = await performanceResponse.json();
            this.updatePerformanceStats();
            this.updateCharts();

        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showNotification('Error loading data', 'error');
        }
    }

    updatePerformanceStats() {
        const { total_signals, winning_signals, losing_signals, total_profit } = this.performanceData;
        
        document.getElementById('total-signals').textContent = total_signals;
        document.getElementById('winning-signals').textContent = winning_signals;
        document.getElementById('losing-signals').textContent = losing_signals;
        document.getElementById('total-profit').textContent = `$${total_profit.toFixed(2)}`;
        
        const winRate = total_signals > 0 ? 
            ((winning_signals / total_signals) * 100).toFixed(1) : 0;
        document.getElementById('win-rate').textContent = `${winRate}%`;
    }

    updateCharts() {
        // Update performance chart
        if (this.performanceChart) {
            const newLabel = new Date().toLocaleTimeString();
            this.performanceChart.data.labels.push(newLabel);
            this.performanceChart.data.datasets[0].data.push(this.performanceData.total_profit);
            
            if (this.performanceChart.data.labels.length > 20) {
                this.performanceChart.data.labels.shift();
                this.performanceChart.data.datasets[0].data.shift();
            }
            
            this.performanceChart.update('none');
        }

        // Update distribution chart
        if (this.distributionChart) {
            const buySignals = this.signals.filter(s => s.direction === 'BUY').length;
            const sellSignals = this.signals.filter(s => s.direction === 'SELL').length;
            
            this.distributionChart.data.datasets[0].data = [buySignals, sellSignals];
            this.distributionChart.update('none');
        }
    }

    addSignalToUI(signal) {
        const signalsContainer = document.getElementById('signals-container');
        const signalElement = this.createSignalElement(signal);
        
        signalsContainer.insertBefore(signalElement, signalsContainer.firstChild);
        
        // Keep only last 20 signals visible
        if (signalsContainer.children.length > 20) {
            signalsContainer.removeChild(signalsContainer.lastChild);
        }
        
        this.updateLastUpdateTime();
    }

    createSignalElement(signal) {
        const div = document.createElement('div');
        div.className = 'signal new-signal';
        div.innerHTML = `
            <div>${signal.timestamp}</div>
            <div>${signal.asset}</div>
            <div class="${signal.direction.toLowerCase()}">${signal.direction}</div>
            <div>${signal.timeframe}</div>
            <div>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${signal.confidence}%"></div>
                    <div class="confidence-text">${signal.confidence}%</div>
                </div>
            </div>
        `;
        
        // Remove animation class after animation completes
        setTimeout(() => {
            div.classList.remove('new-signal');
        }, 500);
        
        return div;
    }

    displaySignals(signals) {
        const container = document.getElementById('signals-container');
        container.innerHTML = '';
        
        signals.forEach(signal => {
            const signalElement = this.createSignalElement(signal);
            container.appendChild(signalElement);
        });
    }

    filterSignals(asset) {
        const filtered = asset === 'all' ? 
            this.signals : 
            this.signals.filter(s => s.asset === asset);
        
        this.displaySignals(filtered);
    }

    searchSignals(query) {
        const filtered = this.signals.filter(s => 
            s.asset.toLowerCase().includes(query.toLowerCase()) ||
            s.direction.toLowerCase().includes(query.toLowerCase()) ||
            s.timeframe.includes(query)
        );
        
        this.displaySignals(filtered);
    }

    updateConnectionStatus(status, className) {
        const statusElement = document.getElementById('status');
        statusElement.textContent = status;
        statusElement.className = className;
    }

    updateLastUpdateTime() {
        document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
    }

    showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `notification-badge ${type}`;
        notification.textContent = message;
        notification.style.background = type === 'error' ? '#e74c3c' : '#27ae60';
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.tradingDashboard = new TradingDashboard();
});
