import os
from datetime import datetime

import pytz

from .client import get_client, heading, paragraph, divider, bulleted_item, price_table, _fmt_price, _fmt_pct


def post_daily_report(
    price_data: list[dict],
    news_items: list[dict],
    dry_run: bool = False,
) -> str | None:
    """
    日次マーケットレポートを Notion に投稿する。
    dry_run=True のときはコンソール出力のみ行い Notion への投稿は行わない。
    """
    jst = pytz.timezone("Asia/Tokyo")
    now_jst = datetime.now(jst)
    title = now_jst.strftime("%Y-%m-%d") + " マーケットレポート"

    if dry_run:
        _print_dry_run(title, price_data, news_items, now_jst)
        return None

    blocks = _build_blocks(price_data, news_items, now_jst)
    db_id = os.environ.get("NOTION_MARKET_REPORT_DB_ID", "")
    if not db_id:
        raise ValueError(
            "NOTION_MARKET_REPORT_DB_ID が設定されていません。"
            "環境変数または .env ファイルに設定してください。"
        )

    client = get_client()
    page = client.pages.create(
        parent={"database_id": db_id},
        properties=_build_properties(title, price_data, now_jst),
        children=blocks,
    )
    url = page["url"]
    print(f"[OK] レポート作成: {url}")
    return url


def _build_properties(title: str, price_data: list[dict], now_jst: datetime) -> dict:
    by_name = {item["name"]: item for item in price_data}

    def _num(ticker_name: str, key: str) -> float | None:
        val = by_name.get(ticker_name, {}).get(key, "N/A")
        return None if val == "N/A" else float(val)

    props: dict = {
        "レポート日付": {"title": [{"text": {"content": title}}]},
        "日付":         {"date": {"start": now_jst.strftime("%Y-%m-%d")}},
        "ステータス":   {"select": {"name": "自動生成"}},
    }

    # 数値プロパティ（前日比(%)は Notion の percent 形式のため 100 で割って渡す）
    _set_number(props, "日経225終値",      _num("日経225", "close"))
    _set_number(props, "日経225前日比(%)", _num("日経225", "change_pct"), scale=0.01)
    _set_number(props, "S&P500終値",       _num("S&P500",  "close"))
    _set_number(props, "S&P500前日比(%)",  _num("S&P500",  "change_pct"), scale=0.01)
    _set_number(props, "USD/JPY",          _num("USD/JPY", "close"))
    _set_number(props, "USD/JPY前日比(%)", _num("USD/JPY", "change_pct"), scale=0.01)

    return props


def _set_number(props: dict, key: str, val: float | None, scale: float = 1.0) -> None:
    if val is not None:
        props[key] = {"number": val * scale}


def _build_blocks(price_data: list[dict], news_items: list[dict], now_jst: datetime) -> list:
    blocks = [
        heading(2, "価格サマリー"),
        price_table(price_data),
        divider(),
        heading(2, "ニュース"),
    ]
    for item in news_items:
        blocks.append(bulleted_item(f"{item['title']}  ({item['source']})"))
    blocks += [
        divider(),
        paragraph(
            f"実行日時: {now_jst.strftime('%Y-%m-%d %H:%M')} JST"
            "  |  データソース: yfinance, RSS"
        ),
    ]
    return blocks


def _print_dry_run(title: str, price_data: list[dict], news_items: list[dict], now_jst: datetime) -> None:
    sep = "=" * 50
    print(f"\n{sep}")
    print(f"[DRY RUN] {title}")
    print(sep)

    print("\n【価格サマリー】")
    header = f"{'銘柄':<10} {'終値':>12} {'前日比':>9} {'週比':>9} {'高値(1M)':>12} {'安値(1M)':>12}"
    print(header)
    print("-" * len(header))
    for item in price_data:
        print(
            f"{item['name']:<10} "
            f"{_fmt_price(item['close']):>12} "
            f"{_fmt_pct(item['change_pct']):>9} "
            f"{_fmt_pct(item['week_change_pct']):>9} "
            f"{_fmt_price(item['high_1m']):>12} "
            f"{_fmt_price(item['low_1m']):>12}"
        )

    print("\n【ニュース】")
    for i, item in enumerate(news_items, 1):
        print(f"{i:2}. {item['title']}  ({item['source']})")
        if item["url"]:
            print(f"    {item['url']}")

    print(f"\n実行日時: {now_jst.strftime('%Y-%m-%d %H:%M')} JST  |  データソース: yfinance, RSS")
    print(sep)
