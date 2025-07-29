from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import requests
import finnhub

app = FastAPI()

# Allow CORS (Frontend can connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can change this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your API keys
NEWS_API_KEY = "58d87c9c00754546b90355c05037349e"
FINNHUB_API_KEY = "d241fphr01qv4g02pom0d241fphr01qv4g02pomg"

# Setup Finnhub client
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

@app.get("/scan")
def scan_stocks():
    # List of stock symbols to check — you can expand this
    stock_list = ["AAPL", "TSLA", "AMD", "PLTR", "NVDA", "RIOT", "MARA", "NKLA", "BBBY", "GME", "AMC"]

    matching_stocks = []

    for symbol in stock_list:
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="60d")

            if len(hist) < 50:
                continue

            current_price = hist['Close'][-1]
            avg_50 = hist['Close'][-50:].mean()
            volume_today = hist['Volume'][-1]
            avg_volume = hist['Volume'].mean()

            # Get float (share outstanding) from Finnhub
            try:
                profile = finnhub_client.company_profile2(symbol=symbol)
                float_shares = profile.get("shareOutstanding", 0) * 1_000_000
            except Exception as e:
                print(f"Finnhub error for {symbol}: {e}")
                float_shares = 0

            # Skip if float not found or over 20 million
            if float_shares == 0 or float_shares > 20_000_000:
                continue

            # Check if price and volume criteria are met
            if (
                current_price >= 1 and current_price <= 20 and
                volume_today >= 5 * avg_volume and
                current_price >= 1.1 * avg_50
            ):
                # Check for recent news using NewsAPI
                try:
                    news_url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey={NEWS_API_KEY}"
                    news = requests.get(news_url).json()
                    if news.get("totalResults", 0) > 0:
                        headline = news["articles"][0]["title"]
                    else:
                        continue
                except Exception as e:
                    print(f"NewsAPI error for {symbol}: {e}")
                    continue

                # Passed all filters — add to results
                matching_stocks.append({
                    "symbol": symbol,
                    "price": round(current_price, 2),
                    "volume_today": int(volume_today),
                    "avg_volume": int(avg_volume),
                    "float": int(float_shares),
                    "news_headline": headline
                })

        except Exception as e:
            print(f"Error checking {symbol}: {e}")
            continue

    return {"results": matching_stocks}

