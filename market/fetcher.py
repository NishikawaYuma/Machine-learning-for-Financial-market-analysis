import yfinance as yf

TICKERS = {
    "日経225": "^N225",
    "S&P500":  "^GSPC",
    "USD/JPY": "USDJPY=X",
    "VIX":     "^VIX",
}


def fetch_price_summary() -> list[dict]:
    """3銘柄の価格サマリーを返す。取得失敗した銘柄は N/A エントリで埋める。"""
    results = []
    for name, ticker in TICKERS.items():
        try:
            results.append(_fetch_single(name, ticker))
        except Exception as e:
            print(f"[ERROR] {name}({ticker}) 取得失敗: {e}")
            results.append(_na_entry(name, ticker))
    return results


def _fetch_single(name: str, ticker: str) -> dict:
    hist = yf.Ticker(ticker).history(period="1mo", interval="1d")
    close_series = hist["Close"].dropna()
    if len(close_series) < 2:
        raise ValueError("データ不足")

    close = float(close_series.iloc[-1])
    prev_close = float(close_series.iloc[-2])
    week_idx = -min(6, len(close_series))
    week_ago = float(close_series.iloc[week_idx])

    high_1m = float(hist["High"].max())
    low_1m = float(hist["Low"].min())
    change_pct = (close - prev_close) / prev_close * 100
    week_change_pct = (close - week_ago) / week_ago * 100

    return {
        "name": name,
        "ticker": ticker,
        "close": close,
        "change_pct": round(change_pct, 2),
        "week_change_pct": round(week_change_pct, 2),
        "high_1m": high_1m,
        "low_1m": low_1m,
    }


def _na_entry(name: str, ticker: str) -> dict:
    return {
        "name": name,
        "ticker": ticker,
        "close": "N/A",
        "change_pct": "N/A",
        "week_change_pct": "N/A",
        "high_1m": "N/A",
        "low_1m": "N/A",
    }
