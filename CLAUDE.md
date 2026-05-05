# CLAUDE.md

## プロジェクト概要

金融市場の日次データ（日経225・S&P500・USD/JPY）を yfinance と RSS で収集し、
Notion の「日次マーケットレポート」DB に毎日自動投稿するシステム。
GitHub Actions で平日 JST 8:00 / 19:00 に自動実行する。

---

## 技術スタック

### V1（現在実装中）

| カテゴリ | ライブラリ / サービス | 用途 |
|---|---|---|
| 価格データ取得 | `yfinance` | 日経225・S&P500・USD/JPY の OHLCV 取得 |
| ニュース取得 | `feedparser` | RSS フィードのパース |
| Notion 連携 | `notion-client` | Notion API へのページ作成 |
| データ処理 | `pandas` | 価格データの整形・計算 |
| 環境変数管理 | `python-dotenv` | `.env` ファイルの読み込み |
| タイムゾーン処理 | `pytz` | JST ↔ UTC 変換 |
| 自動実行 | GitHub Actions | 平日 JST 8:00 / 19:00 のスケジュール実行 |

### V2 以降（今は実装しない）

| カテゴリ | ライブラリ | 用途 |
|---|---|---|
| ML モデル | `scikit-learn` | 価格予測モデルの構築・評価 |
| 可視化 | `matplotlib` | チャート生成 |

---

## コマンド

```bash
# 通常実行（Notion にページを作成する）
python daily_report.py

# 動作確認（データ取得のみ・Notion への投稿はしない）
python daily_report.py --dry-run

# 依存ライブラリのインストール
pip install -r requirements.txt
```

---

## 環境変数

`.env` ファイルに設定する（`.env.example` 参照）。

| 変数名 | 内容 |
|--------|------|
| `NOTION_TOKEN` | Notion Integration Token |
| `NOTION_MARKET_REPORT_DB_ID` | 日次マーケットレポート DB の ID |

---

## Notion DB ID 一覧

| DB / ページ名 | ID |
|---|---|
| ハブページ | `3574cd1b-9fd9-81c4-92f5-d74d8ce7dc0b` |
| 進捗ログ | `6fb84fa6-010c-4317-affb-bc76871a12ef` |
| 分析レポート | `dea248bc-775a-4fe5-b691-d85795e1e4c7` |
| 日次マーケットレポート | `8845e938-92a0-4a6d-b813-5cdb034f564f` |
| 銘柄・データソース一覧 | `e9f0d144-ec7f-43cb-8bb8-5c1905a33ca4` |

---

## V1 スコープ（今作るもの）

- 価格取得: yfinance（終値・前日比・週比・高値・安値）
- ニュース: 無料 RSS のみ（API キー不要）
- 投稿先: 日次マーケットレポート DB のみ

## V2 以降（今は実装しない）

テクニカル指標・センチメント分析・個別株追加・ML 予測

---

## エラー処理方針

データ取得が一部失敗しても、スクリプトを止めずに続行する。

- **価格データ（yfinance）**: 銘柄ごとに取得を試み、失敗した銘柄は `N/A` としてページに記録する。
- **ニュース（RSS）**: フィードごとに取得を試み、失敗したフィードはスキップして残りのフィードから収集する。
- いずれの場合も、エラー内容はコンソール（GitHub Actions のログ）に出力する。
- Notion へのページ作成自体が失敗した場合のみ、例外を上げてスクリプトを終了する。
