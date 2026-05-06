import os
from datetime import datetime

import pytz

from .client import get_client, heading, paragraph, divider, callout, toggle_item, embed_block, price_table, volume_table, _fmt_price, _fmt_pct, _fmt_volume, _pct_color


def post_daily_report(
    price_data: list[dict],
    news_items: list[dict],
    volume_rankings: dict | None = None,
    chart_urls: dict | None = None,
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
        _print_dry_run(title, price_data, news_items, volume_rankings, now_jst)
        return None

    blocks = _build_blocks(price_data, news_items, volume_rankings, chart_urls, now_jst)
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


def _build_blocks(
    price_data: list[dict],
    news_items: list[dict],
    volume_rankings: dict | None,
    chart_urls: dict | None,
    now_jst: datetime,
) -> list:
    blocks = [
        callout(_build_summary_rich_text(price_data), emoji="📊"),
        heading(2, "📈 価格サマリー"),
        price_table(price_data),
        divider(),
    ]

    if chart_urls:
        blocks += _build_chart_section(chart_urls)

    if volume_rankings:
        jp = volume_rankings.get("jp", {})
        us = volume_rankings.get("us", {})
        if jp.get("items"):
            blocks += [
                heading(2, f"🏆 日本株 出来高ランキング TOP10（{jp['date']}）"),
                volume_table(jp["items"], currency="JPY"),
                divider(),
            ]
        if us.get("items"):
            blocks += [
                heading(2, f"🏆 米国株 出来高ランキング TOP10（{us['date']}）"),
                volume_table(us["items"], currency="USD"),
                divider(),
            ]

    blocks.append(heading(2, "📰 ニュース"))
    for item in news_items:
        blocks.append(toggle_item(item["title"], item["url"], item["source"]))
    blocks += [
        divider(),
        paragraph(
            f"実行日時: {now_jst.strftime('%Y-%m-%d %H:%M')} JST"
            "  |  データソース: yfinance, RSS"
        ),
    ]
    return blocks


_CHART_TICKER_META = [
    ("日経225", "📈"),
    ("VIX",     "🌡️"),
    ("S&P500",  "📊"),
]


def _build_chart_section(chart_urls: dict) -> list:
    blocks: list = [heading(2, "📉 チャート")]
    for name, emoji in _CHART_TICKER_META:
        url = chart_urls.get(name)
        blocks.append(heading(3, f"{emoji} {name}"))
        blocks.append(embed_block(url) if url else paragraph("データ取得に失敗しました"))
    blocks.append(divider())
    return blocks


def _build_summary_rich_text(price_data: list[dict]) -> list:
    spans = []
    for i, item in enumerate(price_data):
        if i > 0:
            spans.append({"text": {"content": "  |  "}})
        spans.append({"text": {"content": f"{item['name']}: {_fmt_price(item['close'])}  "}})
        spans.append({
            "text": {"content": _fmt_pct(item["change_pct"])},
            "annotations": {"color": _pct_color(item["change_pct"])},
        })
    return spans


def _print_dry_run(
    title: str,
    price_data: list[dict],
    news_items: list[dict],
    volume_rankings: dict | None,
    now_jst: datetime,
) -> None:
    sep = "=" * 50
    print(f"\n{sep}")
    print(f"[DRY RUN] {title}")
    print(sep)
    summary_parts = []
    for item in price_data:
        summary_parts.append(f"{item['name']}: {_fmt_price(item['close'])}  {_fmt_pct(item['change_pct'])}")
    print(f"\n[Summary] {'  |  '.join(summary_parts)}")

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

    if volume_rankings:
        for market_key, label, currency in [("jp", "日本株", "JPY"), ("us", "米国株", "USD")]:
            mkt = volume_rankings.get(market_key, {})
            if not mkt.get("items"):
                continue
            print(f"\n【{label} 出来高ランキング TOP10（{mkt['date']}）】")
            header = f"{'順位':>4}  {'ティッカー':<10} {'銘柄名':<20} {'終値':>12} {'出来高':>10}"
            print(header)
            print("-" * len(header))
            for i, item in enumerate(mkt["items"], 1):
                ticker_display = item["ticker"].replace(".T", "")
                close_str = f"JPY{item['close']:,.0f}" if currency == "JPY" else f"USD{item['close']:,.2f}"
                print(
                    f"{i:4}.  {ticker_display:<10} {item['name']:<20} "
                    f"{close_str:>12} {_fmt_volume(item['volume']):>10}"
                )

    print("\n【ニュース】")
    for i, item in enumerate(news_items, 1):
        print(f"{i:2}. {item['title']}")
        print(f"    ({item['source']})")
        if item["url"]:
            print(f"    {item['url']}")

    print(f"\n実行日時: {now_jst.strftime('%Y-%m-%d %H:%M')} JST  |  データソース: yfinance, RSS")
    print(sep)
