# app.py
from concurrent.futures import ThreadPoolExecutor
import os

from flask import Flask, jsonify, render_template
from flask_cors import CORS
import backend  # logic

app = Flask(__name__)
CORS(app)  # allow frontend requests

@app.route('/')
def index():
    return render_template('index.html', symbols=backend.NSE_SYMBOLS)

@app.route('/api/symbols')
def get_symbols():
    return jsonify(backend.NSE_SYMBOLS)

@app.route('/api/stock/<symbol>')
def stock_data(symbol):
    symbol = symbol.upper()

    # 1. Fetch historical data ONCE (The foundation)
    hist_data = backend.get_historical_data(symbol, period="6mo")
    live = backend.get_live_stock_data(symbol)

    if not live or hist_data is None:
        return jsonify({'error': 'Could not fetch data'}), 404

    # 🔴 I REMOVED the stray 'return' that was right here!

    # 2. Run calculations and network calls in parallel
    with ThreadPoolExecutor() as executor:
        # Task A: AI Prediction logic
        future_pred = executor.submit(backend.predict_stock_movement, hist_data)

        # Task B: Risk Analysis
        future_risk = executor.submit(backend.analyze_risk, symbol, live['current'], hist_data)

        # Task C: Fetch News
        future_news = executor.submit(backend.fetch_live_news, f"{symbol} share price NSE")

        # Get results
        prediction = future_pred.result()
        risk = future_risk.result()
        news_df = future_news.result()

    # 3. Calculate sentiment and fetch Gemini Summary
    news_list = news_df.head(5).to_dict(orient='records')

    # Calculate overall sentiment from the news headlines
    if news_list:
        avg_score = sum(item['score'] for item in news_list) / len(news_list)
        overall_sentiment = "Positive" if avg_score > 0.05 else "Negative" if avg_score < -0.05 else "Neutral"
    else:
        overall_sentiment = "Neutral"

    # 🟢 UNCOMMENTED the AI Summary call
    ai_summary = backend.get_ai_summary(symbol, prediction, risk, overall_sentiment)

    # 4. Final Blockchain & Return
    block = backend.prediction_blockchain.add_block(symbol, prediction['action'], risk['risk_score'], live['current'], prediction['confidence'])

    return jsonify({
        'live': live,
        'prediction': prediction,
        'risk': risk,
        'news': news_list,
        'ai_summary': ai_summary,
        'blockchain_last_block': block
    })

@app.route('/api/chart/<symbol>')
def chart(symbol):
    symbol = symbol.upper()
    img_base64 = backend.get_price_chart_base64(symbol)
    if img_base64:
        return jsonify({'chart': img_base64})
    else:
        return jsonify({'error': 'Chart not available'}), 404

@app.route('/api/blockchain')
def blockchain():
    return jsonify(backend.prediction_blockchain.get_chain())

if __name__ == '__main__':
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=5000)