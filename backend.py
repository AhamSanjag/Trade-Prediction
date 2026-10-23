# backend.py
import base64
import datetime
import hashlib
import io
import os
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv
from google import genai
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from textblob import TextBlob

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ---------- Blockchain  ----------
class StockPredictionBlockchain:
    def __init__(self):
        self.chain = []
        self.create_genesis_block()
    def create_genesis_block(self):
        genesis_block = {
            'index': 0,
            'timestamp': str(datetime.datetime.now()),
            'data': {'stock_symbol': 'GENESIS', 'prediction': 'Genesis Block', 'risk_score': 0, 'price': 0, 'confidence': 0},
            'previous_hash': '0',
            'hash': self.calculate_hash(0, 'GENESIS', 'Genesis Block', 0, 0, '0')
        }
        self.chain.append(genesis_block)
    def calculate_hash(self, index, stock_symbol, prediction, risk_score, price, previous_hash):
        block_string = f"{index}{stock_symbol}{prediction}{risk_score}{price}{previous_hash}{datetime.datetime.now()}"
        return hashlib.sha256(block_string.encode()).hexdigest()
    def add_block(self, stock_symbol, prediction, risk_score, price, confidence):
        index = len(self.chain)
        previous_hash = self.chain[-1]['hash']
        new_block = {
            'index': index,
            'timestamp': str(datetime.datetime.now()),
            'data': {'stock_symbol': stock_symbol, 'prediction': prediction, 'risk_score': risk_score, 'price': price, 'confidence': confidence},
            'previous_hash': previous_hash,
            'hash': self.calculate_hash(index, stock_symbol, prediction, risk_score, price, previous_hash)
        }
        self.chain.append(new_block)
        return new_block
    def get_chain(self):
        return self.chain
    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            expected_hash = self.calculate_hash(current['index'], current['data']['stock_symbol'],
                                               current['data']['prediction'], current['data']['risk_score'],
                                               current['data']['price'], current['previous_hash'])
            if current['hash'] != expected_hash or current['previous_hash'] != previous['hash']:
                return False
        return True

prediction_blockchain = StockPredictionBlockchain()

# ---------- News  ----------
def fetch_live_news(query="NSE stock market india"):
    try:
        formatted_query = query.replace(' ', '+')
        url = f"https://news.google.com/rss/search?q={formatted_query}&hl=en-IN&gl=IN&ceid=IN:en"
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        news_data = []
        for item in root.findall('./channel/item')[:10]:
            headline = item.find('title').text
            sentiment_score = TextBlob(headline).sentiment.polarity
            sentiment_label = "Positive" if sentiment_score > 0.05 else "Negative" if sentiment_score < -0.05 else "Neutral"
            news_data.append({"headline": headline, "sentiment": sentiment_label, "score": sentiment_score})
        return pd.DataFrame(news_data)
    except Exception as e:
        print(f"⚠️ Could not fetch live news: {e}")
        return pd.DataFrame([{"headline": "Markets closed due to holiday", "sentiment": "Neutral", "score": 0}])

# ---------- Live & Historical Data ----------
def get_live_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol + ".NS")
        data = ticker.history(period="1d", interval="1m")
        if data.empty:
            data = ticker.history(period="2d")
        if data.empty:
            print(f"DEBUG: Yahoo returned empty data for {symbol}.")
            return None
        current = data['Close'].iloc[-1]
        open_price = data['Open'].iloc[0]
        high = data['High'].max()
        low = data['Low'].min()
        volume = data['Volume'].sum()
        change = ((current - open_price) / open_price) * 100
        return {
            'current': float(current),
            'open': float(open_price),
            'high': float(high),
            'low': float(low),
            'volume': int(volume),
            'change': float(change),
            'timestamp': datetime.datetime.now().isoformat()
        }
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
        return None

def get_historical_data(symbol, period="1mo"):
    try:
        ticker = yf.Ticker(symbol + ".NS")
        data = ticker.history(period=period)
        return data
    except Exception as e:
        print(f"❌ Error fetching historical data: {e}")
        return None

# ---------- Prediction  ----------
def predict_stock_movement(historical_data, lookback_days=30):
    if historical_data is None or len(historical_data) < lookback_days + 5:
        return {'action': 'HOLD', 'confidence': 50.0, 'next_price': None, 'predicted_change': 0, 'current_price': None}
    df = historical_data[['Close']].copy()
    df['Return'] = df['Close'].pct_change()
    df['MA_5'] = df['Close'].rolling(window=5).mean()
    df['MA_10'] = df['Close'].rolling(window=10).mean()
    df['Volatility'] = df['Return'].rolling(window=5).std()
    df = df.dropna()
    X, y = [], []
    for i in range(lookback_days, len(df)):
        X.append(df[['Close', 'Return', 'MA_5', 'MA_10', 'Volatility']].iloc[i-lookback_days:i].values.flatten())
        y.append(df['Close'].iloc[i])
    if len(X) < 10:
        return {'action': 'HOLD', 'confidence': 50.0, 'next_price': None, 'predicted_change': 0, 'current_price': df['Close'].iloc[-1]}
    X = np.array(X); y = np.array(y)
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    rf_model = RandomForestRegressor(n_estimators=15, random_state=42)
    rf_model.fit(X_train_scaled, y_train)
    rf_pred = rf_model.predict(X_test_scaled)[-1]
    lr_model = LinearRegression()
    lr_model.fit(X_train_scaled, y_train)
    lr_pred = lr_model.predict(X_test_scaled)[-1]
    final_prediction = (rf_pred + lr_pred) / 2
    current_price = df['Close'].iloc[-1]
    confidence = 85.0 if abs(rf_pred - lr_pred)/current_price < 0.03 else 65.0 if abs(rf_pred - lr_pred)/current_price < 0.07 else 45.0
    predicted_change = ((final_prediction - current_price) / current_price) * 100
    action = "BUY" if predicted_change > 1.5 else "SELL" if predicted_change < -1.5 else "HOLD"
    return {'action': action, 'confidence': confidence, 'next_price': final_prediction,
            'current_price': current_price, 'predicted_change': predicted_change,
            'rf_pred': rf_pred, 'lr_pred': lr_pred}

# ---------- Risk Analysis  ----------
def analyze_risk(symbol, live_price, stock_data):
    market_data = yf.Ticker("^NSEI").history(period="6mo")
    if stock_data is None or stock_data.empty or market_data.empty:
        return {'risk_level': 'MEDIUM', 'risk_score': 5, 'suggestion': 'No data found.', 'stop_loss': 0, 'volatility': 0, 'max_drawdown': 0, 'beta': 1.0}
    clean_stock_prices = stock_data['Close'].dropna()
    if len(clean_stock_prices) < 20:
        return {'risk_level': 'MEDIUM', 'risk_score': 5, 'suggestion': 'Insufficient price history.', 'stop_loss': 0, 'volatility': 0, 'max_drawdown': 0, 'beta': 1.0}
    stock_returns = clean_stock_prices.pct_change().dropna()
    market_returns = market_data['Close'].dropna().pct_change().dropna()
    combined = pd.concat([stock_returns, market_returns], axis=1).dropna()
    combined.columns = ['stock', 'market']
    if not combined.empty and combined['market'].var() != 0:
        beta = combined.cov().iloc[0, 1] / combined['market'].var()
    else:
        beta = 1.0
    volatility = stock_returns.std() * np.sqrt(252)
    volatility = 0.20 if np.isnan(volatility) else volatility
    cumulative = (1 + stock_returns).cumprod()
    max_drawdown = ((cumulative - cumulative.expanding().max()) / cumulative.expanding().max()).min()
    max_drawdown = -0.10 if np.isnan(max_drawdown) else max_drawdown
    risk_score = min(10, max(1, round((abs(beta) * 3) + (volatility * 10) + (abs(max_drawdown) * 5))))
    if risk_score <= 3:
        risk_level, suggestion = "LOW", f"Defensive asset. (Beta: {beta:.2f})"
    elif risk_score <= 7:
        risk_level, suggestion = "MEDIUM", f"Market-aligned risk. It tracks Nifty closely (Beta: {beta:.2f}). Standard position sizing recommended."
    else:
        risk_level, suggestion = "HIGH", f"High sensitivity! (Beta: {beta:.2f})"
    stop_loss = live_price * (1 - (volatility * 0.5 + 0.02))
    return {'risk_level': risk_level, 'risk_score': risk_score, 'suggestion': suggestion,
            'volatility': volatility, 'max_drawdown': max_drawdown, 'beta': beta,
            'stop_loss': stop_loss, 'current_price': live_price}

"""------AI Summary-----"""
def get_ai_summary(symbol, prediction, risk, sentiment):

    #  Extract the data
    action = prediction.get('action', 'HOLD')
    confidence = prediction.get('confidence', 50.0)
    risk_level = risk.get('risk_level', 'MEDIUM')
    beta = risk.get('beta', 1.0)

    #  Build a BEGINNER-FRIENDLY prompt
    prompt = f"""
    You are a friendly, encouraging financial mentor. Your goal is to explain stock market data to an absolute beginner who has never traded before.

    Here is the live data my system calculated for the NSE stock '{symbol}':
    - AI Technical Signal: {action} (Confidence: {confidence:.1f}%)
    - Risk Profile: {risk_level} (Market Volatility Score/Beta is {beta:.2f})
    - Live News Sentiment: {sentiment}

    Write a 3-4 sentence summary explaining exactly what this means and what they should do.

    CRITICAL RULES:
    1. Do NOT use complex financial jargon (avoid words like "consolidation", "resistance", "dead cat bounce").
    2. Explain *why* this is the recommendation in simple terms (e.g., if risk is high, explain that the stock price swings wildly).
    3. If the AI signal and the News disagree, gently warn the beginner that the situation is confusing and it might be best to wait.
    4. Start with a relevant, friendly emoji.
    """
    if client is None:
        return f"Our system suggests a {action}, but please be careful as a beginner. Ensure you do your own research before spending money!"

    try:
        # The AI call will take a few seconds. The frontend will show "loading" during this time.
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text

    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        return f"Our system suggests a {action}, but please be careful as a beginner. Ensure you do your own research before spending money!"
# ---------- Chart as base64 image (for frontend) ----------
def get_price_chart_base64(symbol, period="1d"):
    ticker = yf.Ticker(symbol + ".NS")
    data = ticker.history(period=period, interval="5m" if period == "1d" else "15m")
    if len(data) < 2:
        return None
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(data.index, data['Close'], label='Close Price', color='blue', linewidth=2)
    ax.plot(data.index, data['Close'].rolling(window=5).mean(), label='MA5', color='orange', linestyle='--')
    ax.plot(data.index, data['Close'].rolling(window=10).mean(), label='MA10', color='red', linestyle='--')
    # Buy/Sell signals
    ma5 = data['Close'].rolling(window=5).mean()
    ma10 = data['Close'].rolling(window=10).mean()
    buy_signals, sell_signals = [], []
    for i in range(1, len(ma5)):
        if ma5.iloc[i] > ma10.iloc[i] and ma5.iloc[i-1] <= ma10.iloc[i-1]:
            buy_signals.append(data.index[i])
        elif ma5.iloc[i] < ma10.iloc[i] and ma5.iloc[i-1] >= ma10.iloc[i-1]:
            sell_signals.append(data.index[i])
    if buy_signals:
        ax.scatter(buy_signals, data.loc[buy_signals, 'Close'], color='green', marker='^', s=100, label='Buy')
    if sell_signals:
        ax.scatter(sell_signals, data.loc[sell_signals, 'Close'], color='red', marker='v', s=100, label='Sell')
    ax.set_title(f'{symbol} Live Price Chart')
    ax.set_ylabel('Price (₹)')
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_base64

# ---------- NSE symbol list  ----------
def fetch_active_nse_symbols():
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        nse_df = pd.read_csv(io.StringIO(response.text))
        symbols = sorted(nse_df['SYMBOL'].tolist())
        return symbols
    except Exception as e:
        print(f"⚠️ Could not fetch live symbols: {e}")
        return ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "ATGL"]

NSE_SYMBOLS = fetch_active_nse_symbols()