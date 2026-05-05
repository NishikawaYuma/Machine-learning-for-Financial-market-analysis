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


def price_table(price_data: list[dict]) -> dict:
    """価格サマリーの Notion テーブルブロックを返す。"""
    headers = ["銘柄", "終値", "前日比(%)", "週比(%)", "高値(1M)", "安値(1M)"]
    header_row = _table_row([_cell(h) for h in headers])

    data_rows = [
        _table_row([
            _cell(item["name"]),
            _cell(_fmt_price(item["close"])),
            _cell(_fmt_pct(item["change_pct"])),
            _cell(_fmt_pct(item["week_change_pct"])),
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


def _fmt_price(val) -> str:
    if val == "N/A":
        return "N/A"
    return f"{float(val):,.2f}"


def _fmt_pct(val) -> str:
    if val == "N/A":
        return "N/A"
    sign = "+" if float(val) >= 0 else ""
    return f"{sign}{float(val):.2f}%"
