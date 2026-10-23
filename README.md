# Indian Stock Market Live Trading Assistant

A Flask web app that displays NSE stock data, model-based price estimates, a basic risk analysis, recent news sentiment, and a prediction log. It uses AI to summarize the analysis in beginner-friendly language.

> This project is for learning and demonstration only. It is not financial advice, and predictions can be inaccurate. Verify information independently before making financial decisions.

## Requirements

- Python 3.10 or newer
- Internet access for NSE symbol lists, Yahoo Finance market data, and Google News RSS
- A Gemini API key is optional. Without one, the app uses a built-in fallback summary.

## Run locally

1. Clone the repository and open a terminal in its folder.
2. Create and activate a virtual environment:

   **Windows PowerShell**

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS / Linux**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. (Optional) Configure Gemini summaries. Copy `.env.example` to `.env` and add your own key:

   ```dotenv
   GEMINI_API_KEY=your_key_here
   ```

   Keep `.env` private; it is excluded from Git.

5. Start the app:

   ```bash
   python app.py
   ```

6. Open <http://127.0.0.1:5000> in your browser.

## Notes

- Market data and news require external services and may be delayed, unavailable, or rate-limited.
- If a selected stock has no recent data, try another NSE symbol or try again later.
- `FLASK_DEBUG=1` enables Flask's development debugger; leave it unset for normal local use and never enable it on a public deployment.
- Do not commit API keys, `.env` files, virtual environments, or generated files.
