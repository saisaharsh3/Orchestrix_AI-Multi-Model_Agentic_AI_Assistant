"""
finance_tool.py - Currency conversion and stock prices
Uses:
  - exchangerate-api.com (free, no key needed for basic)
  - Yahoo Finance via yfinance (free, no key needed)

Install: pip install yfinance requests
"""

import requests
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


# -- Currency conversion ------------------------------------------------------

def convert_currency(amount: float, from_curr: str, to_curr: str) -> str:
    from_curr = from_curr.upper()
    to_curr   = to_curr.upper()

    try:
        r = requests.get(
            f"https://open.er-api.com/v6/latest/{from_curr}",
            timeout=10,
        )
        if r.status_code != 200:
            return f"Error: Could not fetch exchange rate for {from_curr}."

        data = r.json()
        if data.get("result") != "success":
            return f"Error: {data.get('error-type', 'Unknown error')}"

        rates = data.get("rates", {})
        if to_curr not in rates:
            return f"Error: Currency '{to_curr}' not found."

        rate        = rates[to_curr]
        converted   = amount * rate
        update_time = data.get("time_last_update_utc", "unknown")

        return (
            f"{amount} {from_curr} = {converted:.2f} {to_curr}\n"
            f"Rate: 1 {from_curr} = {rate:.4f} {to_curr}\n"
            f"Updated: {update_time}"
        )

    except requests.exceptions.ConnectionError:
        return "Error: No internet connection."
    except Exception as e:
        return f"Error converting currency: {e}"


# -- Stock prices -------------------------------------------------------------

def get_stock_price(ticker: str) -> str:
    if not YFINANCE_AVAILABLE:
        return "Error: yfinance not installed. Run: pip install yfinance"

    ticker = ticker.upper()

    # Common Indian stock ticker fixes
    indian_fixes = {
        "TCS":        "TCS.NS",
        "INFOSYS":    "INFY.NS",
        "INFY":       "INFY.NS",
        "RELIANCE":   "RELIANCE.NS",
        "WIPRO":      "WIPRO.NS",
        "HDFC":       "HDFCBANK.NS",
        "HDFCBANK":   "HDFCBANK.NS",
        "ICICIBANK":  "ICICIBANK.NS",
        "TATAMOTORS": "TATAMOTORS.NS",
        "BAJFINANCE": "BAJFINANCE.NS",
    }
    ticker = indian_fixes.get(ticker, ticker)

    try:
        stock = yf.Ticker(ticker)
        info  = stock.info

        price    = info.get("currentPrice") or info.get("regularMarketPrice")
        currency = info.get("currency", "USD")
        name     = info.get("longName") or info.get("shortName") or ticker
        change   = info.get("regularMarketChangePercent", 0)
        high     = info.get("dayHigh")
        low      = info.get("dayLow")
        volume   = info.get("regularMarketVolume")

        if price is None:
            return f"Error: Could not fetch price for '{ticker}'. Check the ticker symbol."

        direction = "+" if change >= 0 else ""
        vol_str   = f"{volume:,}" if volume else "N/A"

        return (
            f"{name} ({ticker})\n"
            f"Price  : {price:.2f} {currency} ({direction}{change:.2f}%)\n"
            f"Day H/L: {high:.2f} / {low:.2f}\n"
            f"Volume : {vol_str}"
        )

    except Exception as e:
        return f"Error fetching stock data for '{ticker}': {e}"


def get_crypto_price(symbol: str) -> str:
    """Get crypto price e.g. BTC, ETH, SOL"""
    if not YFINANCE_AVAILABLE:
        return "Error: yfinance not installed. Run: pip install yfinance"

    symbol = symbol.upper()
    ticker = f"{symbol}-USD"

    try:
        crypto = yf.Ticker(ticker)
        info   = crypto.info
        price  = info.get("currentPrice") or info.get("regularMarketPrice")
        change = info.get("regularMarketChangePercent", 0)

        if price is None:
            return f"Error: Could not fetch price for {symbol}."

        direction = "+" if change >= 0 else ""
        return (
            f"{symbol}/USD\n"
            f"Price : ${price:,.2f}\n"
            f"Change: {direction}{change:.2f}%"
        )

    except Exception as e:
        return f"Error fetching crypto price for {symbol}: {e}"