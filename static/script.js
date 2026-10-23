// static/script.js
const loadBtn = document.getElementById('load-btn');
const stockInput = document.getElementById('stock-input');
const loadingDiv = document.getElementById('loading');
const dashboardDiv = document.getElementById('dashboard');

async function fetchStockData(symbol) {
    loadingDiv.classList.remove('hidden');
    dashboardDiv.classList.add('hidden');

    try {
        // 🚀 SPEED FIX: Fetch both endpoints at the exact same time (Concurrently)
        const [stockRes, chartRes] = await Promise.all([
            fetch(`/api/stock/${symbol}`),
            fetch(`/api/chart/${symbol}`)
        ]);

        if (!stockRes.ok) throw new Error('Stock not found or API error');

        // Parse the JSON data
        const data = await stockRes.json();

        // Only try to parse the chart if the response was successful
        let chartData = null;
        if (chartRes.ok) {
            chartData = await chartRes.json();
        }

        // 🎨 Update the UI
        updateLiveData(data.live);
        updatePrediction(data.prediction);
        updateRisk(data.risk);
        // Ensure we pass the overall sentiment calculated in your backend
        const overallSentiment = data.overall_sentiment || "Neutral";
        updateNews(data.news, overallSentiment);
        updateBlockchain(data.blockchain_last_block);

        // 🤖 Update AI Summary
        updateAiSummary(data.ai_summary);

        // 📊 Chart handling
        const chartImg = document.getElementById('chart-img');
        if (chartData && chartData.chart) {
            chartImg.src = 'data:image/png;base64,' + chartData.chart;
            chartImg.classList.remove('hidden');
        } else {
            chartImg.src = '';
            chartImg.classList.add('hidden');
        }

        // Show the dashboard
        dashboardDiv.classList.remove('hidden');

    } catch (err) {
        alert('Error: ' + err.message);
        console.error(err);
    } finally {
        loadingDiv.classList.add('hidden');
    }
}

// --- EVENT LISTENERS ---

// Enter Key Support
stockInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        const symbol = stockInput.value.trim().toUpperCase();
        if (symbol) fetchStockData(symbol);
    }
});

// Button Click Support
loadBtn.addEventListener('click', () => {
    const symbol = stockInput.value.trim().toUpperCase();
    if (symbol) fetchStockData(symbol);
    else alert('Please enter a stock symbol');
});

// Load a default symbol on page load
window.addEventListener('load', () => {
    stockInput.value = 'TCS';
    fetchStockData('TCS');
});


// --- UI UPDATE FUNCTIONS ---

function updateLiveData(live) {
    const container = document.getElementById('live-data');
    const changeClass = live.change >= 0 ? 'text-green-600' : 'text-red-600';
    container.innerHTML = `
        <div class="grid grid-cols-2 gap-2">
            <div><span class="font-medium">💰 Current:</span> ₹${live.current.toFixed(2)}</div>
            <div><span class="font-medium">📈 Open:</span> ₹${live.open.toFixed(2)}</div>
            <div><span class="font-medium">📊 High:</span> ₹${live.high.toFixed(2)}</div>
            <div><span class="font-medium">📉 Low:</span> ₹${live.low.toFixed(2)}</div>
            <div><span class="font-medium">📦 Volume:</span> ${live.volume.toLocaleString()}</div>
            <div><span class="font-medium ${changeClass}">🔄 Change:</span> ${live.change.toFixed(2)}%</div>
        </div>
        <div class="text-xs text-gray-500 mt-2">As of ${new Date(live.timestamp).toLocaleTimeString()}</div>
    `;
}

function updatePrediction(pred) {
    const container = document.getElementById('prediction');
    let actionColor = '';
    if (pred.action === 'BUY') actionColor = 'text-green-700 bg-green-100';
    else if (pred.action === 'SELL') actionColor = 'text-red-700 bg-red-100';
    else actionColor = 'text-yellow-700 bg-yellow-100';

    container.innerHTML = `
        <div class="mb-2"><span class="font-medium">🎯 Action:</span>
            <span class="px-2 py-1 rounded ${actionColor} font-bold">${pred.action}</span>
        </div>
        <div><span class="font-medium">📊 Predicted Next Price:</span> ₹${pred.next_price ? pred.next_price.toFixed(2) : 'N/A'}</div>
        <div><span class="font-medium">📈 Predicted Change:</span> ${pred.predicted_change ? pred.predicted_change.toFixed(2) : '0'}%</div>
        <div><span class="font-medium">✅ Confidence:</span> ${pred.confidence.toFixed(1)}%</div>
    `;
}

function updateRisk(risk) {
    const container = document.getElementById('risk');
    let riskColor = '';
    if (risk.risk_level === 'LOW') riskColor = 'text-green-700';
    else if (risk.risk_level === 'MEDIUM') riskColor = 'text-yellow-700';
    else riskColor = 'text-red-700';

    container.innerHTML = `
        <div class="grid md:grid-cols-2 gap-3">
            <div><span class="font-medium">⚠️ Risk Level:</span> <span class="${riskColor} font-bold">${risk.risk_level} (${risk.risk_score}/10)</span></div>
            <div><span class="font-medium">📊 Volatility:</span> ${(risk.volatility * 100).toFixed(2)}%</div>
            <div><span class="font-medium">📉 Max Drawdown:</span> ${(risk.max_drawdown * 100).toFixed(2)}%</div>
            <div><span class="font-medium">🧭 Beta:</span> ${risk.beta.toFixed(2)}</div>
            <div><span class="font-medium">🛑 Suggested Stop-Loss:</span> ₹${risk.stop_loss.toFixed(2)}</div>
            <div class="col-span-2"><span class="font-medium">💡 Suggestion:</span> ${risk.suggestion}</div>
        </div>
    `;
}

function updateNews(newsList, overall) {
    const container = document.getElementById('news');
    let sentimentBadge = '';
    if (overall === 'Positive') sentimentBadge = '<span class="bg-green-200 text-green-800 px-2 py-1 rounded-full text-sm">📰 Overall: Positive</span>';
    else if (overall === 'Negative') sentimentBadge = '<span class="bg-red-200 text-red-800 px-2 py-1 rounded-full text-sm">📰 Overall: Negative</span>';
    else sentimentBadge = '<span class="bg-gray-200 text-gray-800 px-2 py-1 rounded-full text-sm">📰 Overall: Neutral</span>';

    let newsHtml = `<div class="mb-3">${sentimentBadge}</div><ul class="space-y-2">`;
    newsList.forEach(item => {
        let emoji = item.sentiment === 'Positive' ? '✅' : (item.sentiment === 'Negative' ? '⚠️' : 'ℹ️');
        newsHtml += `<li class="border-b pb-2 text-sm">${emoji} ${item.headline} <span class="text-gray-500 text-xs">(${item.sentiment})</span></li>`;
    });
    newsHtml += '</ul>';
    container.innerHTML = newsHtml;
}

function updateBlockchain(block) {
    const container = document.getElementById('blockchain');
    container.innerHTML = `
        <div><strong>Block #${block.index}</strong> – ${block.timestamp}</div>
        <div>Symbol: ${block.data.stock_symbol} | Prediction: ${block.data.prediction} | Risk: ${block.data.risk_score}/10 | Price: ₹${block.data.price.toFixed(2)} | Confidence: ${block.data.confidence}%</div>
        <div class="text-gray-500 text-xs break-all mt-1">Hash: ${block.hash}</div>
    `;
}

// AI Summary properly restored
function updateAiSummary(summary) {
    const container = document.getElementById('ai-summary-text');
    // Check if the container exists in your HTML before trying to update it
    if (container) {
        if (summary) {
            container.innerHTML = summary;
        } else {
            container.innerHTML = "AI summary is currently unavailable. Please try again in a moment.";
        }
    }
}