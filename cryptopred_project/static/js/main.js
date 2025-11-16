document.addEventListener('DOMContentLoaded', () => {
    const predictForm = document.getElementById('predict-form');
    const chartContainer = document.getElementById('chart-container');
    const predictionResultDiv = document.getElementById('prediction-result');
    const historyList = document.getElementById('history-list');
    const loader = document.getElementById('loader');
    const errorMessage = document.getElementById('error-message');

    let predictionChart = null;

    // --- Core Prediction Logic ---
    if (predictForm) {
        predictForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Show loader and clear previous results/errors
            if(loader) loader.classList.remove('hidden');
            if(errorMessage) errorMessage.classList.add('hidden');
            if(predictionResultDiv) predictionResultDiv.classList.add('hidden');
            
            const coin = document.getElementById('coin-select').value;
            const interval_type = document.getElementById('interval-select').value;

            try {
                const response = await fetch('/api/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ coin, interval_type }),
                });

                if (response.status === 401) {
                    // Session expired or user not logged in, redirect
                    window.location.href = '/login';
                    return;
                }

                const result = await response.json();

                if (!response.ok || !result.success) {
                    throw new Error(result.message || 'An unknown error occurred during prediction.');
                }
                
                displayPrediction(result.data);
                fetchHistory(); // Refresh history list

            } catch (error) {
                console.error('Prediction failed:', error);
                showError(error.message);
            } finally {
                if(loader) loader.classList.add('hidden');
            }
        });
    }

    // --- Chart and Display Logic ---
    function displayPrediction(data) {
        if (!data || !data.predictions || data.predictions.length === 0) {
            showError('No prediction data returned from the server.');
            return;
        }

        if(predictionResultDiv) predictionResultDiv.classList.remove('hidden');
        if(chartContainer && chartContainer.getContext) {
            const labels = data.predictions.map(p => new Date(p.timestamp).toLocaleString());
            const prices = data.predictions.map(p => p.predicted_price_usd);

            if (predictionChart) {
                predictionChart.destroy();
            }

            predictionChart = new Chart(chartContainer, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: `${data.coin.toUpperCase()} Predicted Price (USD)`,
                        data: prices,
                        borderColor: '#8b5cf6', // purple-500
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        tension: 0.1,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            ticks: { color: '#d1d5db' }, // gray-300
                            grid: { color: 'rgba(255, 255, 255, 0.1)' }
                        },
                        x: {
                            ticks: { color: '#d1d5db' }, // gray-300
                            grid: { color: 'rgba(255, 255, 255, 0.1)' }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: '#d1d5db' } }
                    }
                }
            });
        }
    }

    // --- History Logic ---
    async function fetchHistory() {
        if (!historyList) return;

        try {
            const response = await fetch('/api/history');
            
            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }
            
            const result = await response.json();

            if (result.success) {
                renderHistory(result.history);
            } else {
                throw new Error(result.message || 'Failed to fetch history.');
            }
        } catch (error) {
            console.error('Error fetching history:', error);
            historyList.innerHTML = `<li class="text-red-400">${error.message}</li>`;
        }
    }

    function renderHistory(historyData) {
        if (!historyList) return;
        historyList.innerHTML = ''; // Clear current list
        
        if (historyData.length === 0) {
            historyList.innerHTML = '<p class="text-gray-400">No prediction history yet.</p>';
            return;
        }
        
        historyData.forEach(item => {
            const li = document.createElement('li');
            li.className = 'history-item';
            
            const content = `
                <div class="flex-grow">
                    <span class="font-bold text-white">${item.coin.toUpperCase()}</span>
                    <span class="text-sm text-gray-400 ml-2">(${item.interval})</span>
                    <p class="text-xs text-gray-500">${new Date(item.predictions[0].timestamp).toLocaleString()}</p>
                </div>
                <button class="download-csv-btn btn-secondary text-sm" data-history='${JSON.stringify(item.predictions)}'>Download CSV</button>
            `;
            li.innerHTML = content;
            historyList.appendChild(li);
        });
    }
    
    // --- Utility Functions ---
    function showError(message) {
        if (errorMessage) {
            errorMessage.textContent = `Error: ${message}`;
            errorMessage.classList.remove('hidden');
        }
    }

    function downloadCSV(data, coin) {
        const headers = 'timestamp,predicted_price_usd\n';
        const rows = data.map(p => `${p.timestamp},${p.predicted_price_usd}`).join('\n');
        const csvContent = headers + rows;
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `${coin}_prediction_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    // Event delegation for dynamically added download buttons
    if(historyList){
        historyList.addEventListener('click', (e) => {
            if (e.target && e.target.classList.contains('download-csv-btn')) {
                const data = JSON.parse(e.target.dataset.history);
                const coin = e.target.parentElement.querySelector('span.font-bold').textContent;
                downloadCSV(data, coin);
            }
        });
    }

    // Initial fetch of history data if on the predict page
    if (window.location.pathname.endsWith('/predict')) {
        fetchHistory();
    }
});

