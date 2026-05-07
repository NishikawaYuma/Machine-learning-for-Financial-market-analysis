"""
日次マーケットレポート — エントリポイント

使い方:
  python daily_report.py           # Notion にページを作成
  python daily_report.py --dry-run # データ取得のみ（Notion への投稿なし）
"""

import argparse

from dotenv import load_dotenv


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="金融市場 日次レポート")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="データ取得のみ実行し、Notion への投稿は行わない",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = _parse_args()

    from market.fetcher import fetch_price_summary
    from market.news import fetch_news
    from market.volume_ranking import fetch_volume_rankings
    from market.chart import fetch_all_chart_urls
    from notion.daily_report import post_daily_report

    print("価格データ取得中...")
    price_data = fetch_price_summary()

    print("ニュース取得中...")
    news_items = fetch_news(max_items=10)

    print("出来高データ取得中...")
    volume_rankings = fetch_volume_rankings()

    chart_urls = None
    if not args.dry_run:
        print("チャートURL生成中...")
        chart_urls = fetch_all_chart_urls()

    notion_url = post_daily_report(price_data, news_items, volume_rankings, chart_urls, dry_run=args.dry_run)

    if notion_url:
        print("\n=== 投稿サマリー ===")
        print(f"Notion ページ: {notion_url}")
        if chart_urls:
            print("チャートURL:")
            for name, url in chart_urls.items():
                print(f"  {name}: {url if url else '取得失敗'}")


if __name__ == "__main__":
    main()
