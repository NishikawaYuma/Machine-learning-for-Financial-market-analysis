import os
from notion_client import Client


def get_client() -> Client:
    token = os.environ.get("NOTION_TOKEN", "")
    if not token:
        raise ValueError(
            "NOTION_TOKEN が設定されていません。"
            "環境変数 NOTION_TOKEN に Integration Token を設定してください。"
        )
    return Client(auth=token)


# ─── ブロックビルダー ──────────────────────────────────────────

def heading(level: int, text: str) -> dict:
    key = f"heading_{level}"
    return {"type": key, key: {"rich_text": [{"text": {"content": text}}]}, "object": "block"}


def paragraph(text: str) -> dict:
    return {
        "type": "paragraph",
        "paragraph": {"rich_text": [{"text": {"content": text}}]},
        "object": "block",
    }


def divider() -> dict:
    return {"type": "divider", "divider": {}, "object": "block"}


def bulleted_item(text: str) -> dict:
    return {
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"text": {"content": text}}]},
        "object": "block",
    }


def callout(text: str | list, emoji: str = "📊") -> dict:
    rich_text = text if isinstance(text, list) else [{"text": {"content": text}}]
    return {
        "type": "callout",
        "callout": {
            "rich_text": rich_text,
            "icon": {"emoji": emoji},
            "color": "default",
        },
        "object": "block",
    }


def toggle_item(title: str, url: str, source: str) -> dict:
    """ニュース1件: タイトルをトグルブロックにし、ソース名を斜体の子ブロックで表示する。"""
    text_obj: dict = {"content": title}
    if url:
        text_obj["link"] = {"url": url}
    source_block = {
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "text": {"content": source},
                    "annotations": {"italic": True, "color": "gray"},
                }
            ]
        },
        "object": "block",
    }
    return {
        "type": "toggle",
        "toggle": {
            "rich_text": [{"text": text_obj}],
            "children": [source_block],
        },
        "object": "block",
    }


def news_item(title: str, url: str, source: str) -> dict:
    """ニュース1件: タイトルをリンク付き箇条書きにし、ソース名を斜体の子ブロックで表示する。"""
    text_obj: dict = {"content": title}
    if url:
        text_obj["link"] = {"url": url}

    source_block = {
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "text": {"content": source},
                    "annotations": {"italic": True, "color": "gray"},
                }
            ]
        },
        "object": "block",
    }

    return {
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"text": text_obj}],
            "children": [source_block],
        },
        "object": "block",
    }


def price_table(price_data: list[dict]) -> dict:
    """価格サマリーの Notion テーブルブロックを返す。"""
    headers = ["銘柄", "終値", "前日比(%)", "週比(%)", "高値(1M)", "安値(1M)"]
    header_row = _table_row([_cell(h) for h in headers])

    data_rows = [
        _table_row([
            _cell(item["name"]),
            _cell(_fmt_price(item["close"])),
            _colored_cell(_fmt_pct(item["change_pct"]),      _pct_color(item["change_pct"])),
            _colored_cell(_fmt_pct(item["week_change_pct"]), _pct_color(item["week_change_pct"])),
            _cell(_fmt_price(item["high_1m"])),
            _cell(_fmt_price(item["low_1m"])),
        ])
        for item in price_data
    ]

    return {
        "type": "table",
        "table": {
            "table_width": len(headers),
            "has_column_header": True,
            "has_row_header": False,
            "children": [header_row] + data_rows,
        },
        "object": "block",
    }


def _table_row(cells: list) -> dict:
    return {"type": "table_row", "table_row": {"cells": cells}, "object": "block"}


def _cell(text: str) -> list:
    return [{"text": {"content": text}}]


def _colored_cell(text: str, color: str) -> list:
    return [{"text": {"content": text}, "annotations": {"color": color}}]


def _pct_color(val) -> str:
    if val == "N/A":
        return "default"
    return "green" if float(val) >= 0 else "red"


def volume_table(items: list[dict], currency: str = "USD") -> dict:
    """出来高ランキングの Notion テーブルブロックを返す。"""
    headers = ["順位", "ティッカー", "銘柄名", "終値", "出来高"]
    header_row = _table_row([_cell(h) for h in headers])

    data_rows = []
    for i, item in enumerate(items, 1):
        ticker_display = item["ticker"].replace(".T", "")
        if currency == "JPY":
            close_str = f"¥{item['close']:,.0f}"
        else:
            close_str = f"${item['close']:,.2f}"
        data_rows.append(
            _table_row([
                _cell(str(i)),
                _cell(ticker_display),
                _cell(item["name"]),
                _cell(close_str),
                _cell(_fmt_volume(item["volume"])),
            ])
        )

    return {
        "type": "table",
        "table": {
            "table_width": len(headers),
            "has_column_header": True,
            "has_row_header": False,
            "children": [header_row] + data_rows,
        },
        "object": "block",
    }


def toggle(text: str, children: list) -> dict:
    return {
        "type": "toggle",
        "toggle": {
            "rich_text": [{"text": {"content": text}}],
            "children": children,
        },
        "object": "block",
    }


def image_block(url: str) -> dict:
    return {
        "type": "image",
        "image": {"type": "external", "external": {"url": url}},
        "object": "block",
    }


def embed_block(url: str) -> dict:
    return {
        "type": "embed",
        "embed": {"url": url},
        "object": "block",
    }


def _fmt_volume(vol: int) -> str:
    if vol >= 1_000_000:
        return f"{vol / 1_000_000:.1f}M"
    if vol >= 1_000:
        return f"{vol / 1_000:.1f}K"
    return str(vol)


def _fmt_price(val) -> str:
    if val == "N/A":
        return "N/A"
    return f"{float(val):,.2f}"


def _fmt_pct(val) -> str:
    if val == "N/A":
        return "N/A"
    v = float(val)
    mark = "▲" if v >= 0 else "▼"
    sign = "+" if v >= 0 else ""
    return f"{mark}{sign}{v:.2f}%"
