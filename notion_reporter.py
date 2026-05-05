"""
Notion自動レポーター
分析結果をNotionの「分析レポート」DBへ投稿し、
詳細ページにチャートやメトリクスを記録する。
"""

import os
from datetime import datetime
from notion_client import Client

# ─── 設定 ────────────────────────────────────────────────
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")

# Notionのデータソース/データベースID
REPORT_DB_ID       = "dea248bc-775a-4fe5-b691-d85795e1e4c7"   # 分析レポートDB
PROGRESS_DB_ID     = "6fb84fa6-010c-4317-affb-bc76871a12ef"   # 進捗ログDB
HUB_PAGE_ID        = "3574cd1b-9fd9-81c4-92f5-d74d8ce7dc0b"   # ハブページ
# ─────────────────────────────────────────────────────────


def get_client() -> Client:
    token = NOTION_TOKEN
    if not token:
        raise ValueError(
            "NOTION_TOKEN が設定されていません。"
            "環境変数 NOTION_TOKEN に Integration Token を設定してください。"
        )
    return Client(auth=token)


def post_analysis_report(
    report_name: str,
    model_name: str,
    ticker: str,
    metrics: dict,
    detail_markdown: str = "",
    status: str = "自動生成",
) -> str:
    """
    分析レポートDBに1件登録し、詳細ページに内容を書き込む。

    Parameters
    ----------
    report_name     : レポートのタイトル
    model_name      : 使用モデル名 (例: "RandomForest")
    ticker          : 対象銘柄 (例: "7203.T")
    metrics         : 精度指標の辞書 (例: {"RMSE": 0.023, "MAE": 0.018, "R2": 0.81})
    detail_markdown : 詳細説明（Markdownテキスト）
    status          : "自動生成" / "確認済み" / "要確認"

    Returns
    -------
    str : 作成されたページのURL
    """
    client = get_client()
    now_iso = datetime.now().strftime("%Y-%m-%d")
    metrics_str = "  ".join(f"{k}: {v}" for k, v in metrics.items())

    page = client.pages.create(
        parent={"database_id": REPORT_DB_ID},
        properties={
            "レポート名": {"title": [{"text": {"content": report_name}}]},
            "実行日時":   {"date": {"start": now_iso}},
            "モデル":     {"rich_text": [{"text": {"content": model_name}}]},
            "対象銘柄":   {"rich_text": [{"text": {"content": ticker}}]},
            "精度指標":   {"rich_text": [{"text": {"content": metrics_str}}]},
            "ステータス": {"select": {"name": status}},
        },
        children=_build_report_blocks(report_name, model_name, ticker, metrics, detail_markdown),
    )
    url = page["url"]
    print(f"[OK] レポート作成: {url}")
    return url


def add_progress_task(
    task_name: str,
    category: str,
    due_date: str | None = None,
    memo: str = "",
    status: str = "未着手",
) -> str:
    """
    進捗ログDBにタスクを1件追加する。

    Parameters
    ----------
    task_name : タスク名
    category  : "データ収集" / "EDA" / "モデル構築" / "評価" / "インフラ"
    due_date  : 期限 (YYYY-MM-DD 形式、省略可)
    memo      : 補足メモ
    status    : "未着手" / "進行中" / "完了" / "保留"
    """
    client = get_client()
    props = {
        "タスク名":   {"title": [{"text": {"content": task_name}}]},
        "カテゴリ":   {"select": {"name": category}},
        "ステータス": {"select": {"name": status}},
        "メモ":       {"rich_text": [{"text": {"content": memo}}]},
    }
    if due_date:
        props["期限"] = {"date": {"start": due_date}}

    page = client.pages.create(
        parent={"database_id": PROGRESS_DB_ID},
        properties=props,
    )
    url = page["url"]
    print(f"[OK] タスク追加: {url}")
    return url


def update_task_status(page_id: str, new_status: str) -> None:
    """進捗ログDBの既存タスクのステータスを更新する。"""
    client = get_client()
    client.pages.update(
        page_id=page_id,
        properties={"ステータス": {"select": {"name": new_status}}},
    )
    print(f"[OK] ステータス更新 ({page_id[:8]}...) → {new_status}")


# ─── 内部ヘルパー ─────────────────────────────────────────

def _build_report_blocks(
    report_name: str,
    model_name: str,
    ticker: str,
    metrics: dict,
    detail_markdown: str,
) -> list:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    blocks = [
        _heading(2, f"{report_name}"),
        _paragraph(f"実行日時: {now_str}　|　モデル: {model_name}　|　銘柄: {ticker}"),
        _divider(),
        _heading(3, "精度指標"),
        _table_block(metrics),
        _divider(),
    ]
    if detail_markdown:
        blocks.append(_heading(3, "詳細"))
        for line in detail_markdown.strip().splitlines():
            blocks.append(_paragraph(line) if line.strip() else _divider())
    return blocks


def _heading(level: int, text: str) -> dict:
    key = f"heading_{level}"
    return {key: {"rich_text": [{"text": {"content": text}}]}, "type": key, "object": "block"}


def _paragraph(text: str) -> dict:
    return {
        "type": "paragraph",
        "paragraph": {"rich_text": [{"text": {"content": text}}]},
        "object": "block",
    }


def _divider() -> dict:
    return {"type": "divider", "divider": {}, "object": "block"}


def _table_block(metrics: dict) -> dict:
    rows = [
        {
            "type": "table_row",
            "table_row": {"cells": [[{"text": {"content": "指標"}}], [{"text": {"content": "値"}}]]},
            "object": "block",
        }
    ]
    for k, v in metrics.items():
        rows.append({
            "type": "table_row",
            "table_row": {"cells": [[{"text": {"content": str(k)}}], [{"text": {"content": str(v)}}]]},
            "object": "block",
        })
    return {
        "type": "table",
        "table": {
            "table_width": 2,
            "has_column_header": True,
            "has_row_header": False,
            "children": rows,
        },
        "object": "block",
    }


# ─── 使用例 ───────────────────────────────────────────────

if __name__ == "__main__":
    # 分析後にこのように呼び出す
    post_analysis_report(
        report_name="ランダムフォレスト 初回テスト (7203.T)",
        model_name="RandomForestRegressor",
        ticker="7203.T",
        metrics={"RMSE": 0.0231, "MAE": 0.0178, "R²": 0.812},
        detail_markdown=(
            "特徴量: 終値・出来高・MA5・MA20・RSI14\n"
            "訓練期間: 2020-01-01 〜 2024-12-31\n"
            "テスト期間: 2025-01-01 〜 2025-12-31\n"
            "ハイパーパラメータ: n_estimators=200, max_depth=10"
        ),
    )
