# 要件定義 — 金融市場 日次レポート自動化 & Notionプロジェクト管理

## プロジェクト概要

Python を使って金融市場データを毎日自動収集し、Notion にレポートとして投稿するシステムを構築する。
あわせて、Notion をプロジェクト全体の管理拠点として活用する。

---

## 対象市場・銘柄

| 銘柄名 | ティッカー（yfinance） | 市場区分 |
|--------|----------------------|---------|
| 日経225 | `^N225` | 日本株 |
| S&P500 | `^GSPC` | 米国株 |
| USD/JPY | `USDJPY=X` | 為替 |

> 個別株・ETFの追加は V2 以降で対応。

---

## V1（最初に作るもの）

### 機能一覧

| 機能 | 内容 |
|------|------|
| 価格データ取得 | 日経225・S&P500・USD/JPY の終値・前日比・週比・高値・安値を yfinance で取得 |
| ニュース収集 | 無料 RSS フィードから金融ニュース見出しを取得（APIキー不要） |
| Notion 投稿 | 上記データをまとめて「日次マーケットレポート」DB に毎日1ページ作成 |
| 自動実行 | GitHub Actions で平日朝（JST 8:00）・夕方（JST 19:00）の1日2回自動実行 |
| 手動実行 | GitHub の Actions 画面からブラウザ（PC・スマホ）で手動実行 |

### Notion レポートページ構成

```
タイトル: YYYY-MM-DD マーケットレポート
─────────────────────────────
## 価格サマリー
銘柄 | 終値 | 前日比(%) | 週比(%) | 高値(1M) | 安値(1M)
─────────────────────────────
## ニュース
- 見出し1（ソース・URL）
- 見出し2
- ...（最大10件）
─────────────────────────────
実行日時: ...  |  データソース: yfinance, RSS
```

### ニュース RSS フィード（無料・APIキー不要）

| フィード名 | 言語 |
|-----------|------|
| Yahoo Finance JP | 日本語 |
| NHK 経済ニュース | 日本語 |
| Reuters JP | 日本語 |
| Yahoo Finance US | 英語 |

---

## V2 以降（後回し）

| 機能 | 内容 |
|------|------|
| テクニカル指標 | MA(5/20/50)・RSI(14)・MACD をレポートに追加 |
| センチメント分析 | ニュース見出しのポジティブ/ネガティブを自動判定 |
| 個別株の追跡 | 日本株・米国株の個別銘柄をレポート対象に追加 |
| ML 予測 | 機械学習モデルによる翌日・翌週の価格予測 |

---

## 実行方式

- **自動実行**: GitHub Actions cron（平日 1日2回）
  - 朝: UTC 23:00（前日）= JST 8:00
  - 夕: UTC 10:00 = JST 19:00
- **手動実行**: GitHub の Actions タブ → "Run workflow" ボタン（PC・スマホのブラウザから操作可能）
- **ローカル実行**: `python daily_report.py`（開発・デバッグ用）
- **動作確認**: `python daily_report.py --dry-run`（Notion への投稿なし）

---

## Notion 構成

### 既存（セットアップ済み）

| DB / ページ名 | 用途 | Notion ID |
|-------------|------|-----------|
| 機械学習・金融市場分析プロジェクト | ハブページ | `3574cd1b-9fd9-81c4-92f5-d74d8ce7dc0b` |
| 進捗ログ | タスク・マイルストーン管理 | `6fb84fa6-010c-4317-affb-bc76871a12ef` |
| 分析レポート | ML モデルの評価結果（V2 以降で活用） | `dea248bc-775a-4fe5-b691-d85795e1e4c7` |
| 日次マーケットレポート | 毎日の価格・ニュース | `8845e938-92a0-4a6d-b813-5cdb034f564f` |
| 銘柄・データソース一覧 | 対象銘柄とデータ取得元の管理 | `e9f0d144-ec7f-43cb-8bb8-5c1905a33ca4` |

### 今後追加予定

| DB 名 | 用途 |
|-------|------|
| ロードマップ | フェーズ・マイルストーンの進捗管理 |
| 学習メモ・参考文献 | 勉強メモ・参考 URL の蓄積 |

---

## ファイル構成（V1 実装予定）

```
├── daily_report.py              # メインエントリポイント
├── market/
│   ├── __init__.py
│   ├── fetcher.py               # yfinance でデータ取得
│   └── news.py                  # RSS でニュース取得
├── notion/
│   ├── __init__.py
│   ├── client.py                # 共通クライアント・ブロックビルダー
│   └── daily_report.py          # 日次レポート DB への投稿
├── .github/
│   └── workflows/
│       └── daily_report.yml     # GitHub Actions ワークフロー
├── requirements.txt             # 依存ライブラリ
├── .env.example                 # 環境変数テンプレート
├── notion_reporter.py           # 既存（ML 分析レポート用・変更しない）
└── REQUIREMENTS.md              # 本ファイル
```

---

## 環境変数

| 変数名 | 内容 | 取得方法 |
|--------|------|---------|
| `NOTION_TOKEN` | Notion Integration Token | [notion.so/my-integrations](https://www.notion.so/my-integrations) |
| `NOTION_MARKET_REPORT_DB_ID` | 日次マーケットレポート DB ID | Notion DB URL から取得 |

---

## 作業順序

1. `REQUIREMENTS.md` 作成（本ファイル）✅
2. Notion の銘柄・データソース一覧に初期データ投入
3. `requirements.txt` 更新（feedparser・pytz 追加）
4. `market/fetcher.py` — 価格データ取得
5. `market/news.py` — ニュース取得
6. `notion/client.py` — 共通クライアント
7. `notion/daily_report.py` — レポート投稿
8. `daily_report.py` — エントリポイント
9. ローカルテスト（`--dry-run`）
10. GitHub へ push・Actions 設定・手動実行テスト
