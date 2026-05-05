import pandas as pd
import yfinance as yf
from datetime import datetime

US_TICKERS: dict[str, str] = {
    "AAPL":  "Apple",
    "MSFT":  "Microsoft",
    "NVDA":  "NVIDIA",
    "AMZN":  "Amazon",
    "GOOGL": "Alphabet",
    "META":  "Meta",
    "TSLA":  "Tesla",
    "AVGO":  "Broadcom",
    "AMD":   "AMD",
    "INTC":  "Intel",
    "NFLX":  "Netflix",
    "ORCL":  "Oracle",
    "QCOM":  "Qualcomm",
    "MU":    "Micron",
    "AMAT":  "Applied Materials",
    "JPM":   "JPMorgan Chase",
    "BAC":   "Bank of America",
    "GS":    "Goldman Sachs",
    "WFC":   "Wells Fargo",
    "XOM":   "ExxonMobil",
    "CVX":   "Chevron",
    "UNH":   "UnitedHealth",
    "PFE":   "Pfizer",
    "F":     "Ford",
    "T":     "AT&T",
    "DIS":   "Disney",
    "PLTR":  "Palantir",
    "COIN":  "Coinbase",
    "RIVN":  "Rivian",
    "SPY":   "S&P500 ETF",
    "QQQ":   "Nasdaq-100 ETF",
}

JP_TICKERS: dict[str, str] = {
    "7203.T": "トヨタ自動車",
    "6758.T": "ソニーグループ",
    "8306.T": "三菱UFJ FG",
    "9984.T": "ソフトバンクG",
    "6861.T": "キーエンス",
    "7974.T": "任天堂",
    "8035.T": "東京エレクトロン",
    "9432.T": "NTT",
    "9433.T": "KDDI",
    "8316.T": "三井住友FG",
    "8411.T": "みずほFG",
    "4502.T": "武田薬品",
    "6501.T": "日立製作所",
    "7267.T": "ホンダ",
    "6098.T": "リクルートHD",
    "9983.T": "ファーストリテイリング",
    "4519.T": "中外製薬",
    "6902.T": "デンソー",
    "7751.T": "キヤノン",
    "4901.T": "富士フイルム",
    "6954.T": "ファナック",
    "6367.T": "ダイキン工業",
    "4063.T": "信越化学工業",
    "4661.T": "オリエンタルランド",
    "6594.T": "ニデック",
}

_TOP_N = 10


def fetch_volume_rankings() -> dict:
    """
    出来高ランキングを取得する。
    iloc[-1]（直近の完了した取引日）を常に使うことで、
    JST8時実行時は両市場とも前日、JST19時実行時はJP当日・US前日が自然に得られる。

    戻り値: {"us": {"items": [...], "date": "YYYY-MM-DD"}, "jp": {...}}
    """
    print("米国株 出来高データ取得中...")
    us_items, us_date = _fetch_ranking(US_TICKERS, "US")
    print("日本株 出来高データ取得中...")
    jp_items, jp_date = _fetch_ranking(JP_TICKERS, "JP")
    return {
        "us": {"items": us_items, "date": us_date},
        "jp": {"items": jp_items, "date": jp_date},
    }


def _fetch_ranking(
    name_map: dict[str, str],
    market: str,
) -> tuple[list[dict], str]:
    tickers = list(name_map.keys())
    try:
        raw = yf.download(
            tickers,
            period="5d",
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
    except Exception as e:
        print(f"[ERROR] {market}出来高データ取得失敗: {e}")
        return [], "N/A"

    try:
        volume_df = raw["Volume"].dropna(how="all")
        close_df = raw["Close"].dropna(how="all")
    except KeyError:
        print(f"[ERROR] {market}: Volume/Close カラムが見つかりません")
        return [], "N/A"

    if volume_df.empty:
        return [], "N/A"

    trading_date = str(volume_df.index[-1].date())

    results: list[dict] = []
    for ticker in tickers:
        if ticker not in volume_df.columns:
            continue
        try:
            vol = volume_df[ticker].iloc[-1]
            close = close_df[ticker].iloc[-1]
            if pd.isna(vol) or pd.isna(close) or int(vol) == 0:
                continue
            results.append({
                "ticker": ticker,
                "name": name_map[ticker],
                "close": float(close),
                "volume": int(vol),
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["volume"], reverse=True)
    return results[:_TOP_N], trading_date
