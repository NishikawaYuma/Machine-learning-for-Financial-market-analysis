import feedparser

RSS_FEEDS = [
    {"name": "Yahoo News JP 経済", "url": "https://news.yahoo.co.jp/rss/categories/business.xml"},
    {"name": "NHK 経済",           "url": "https://www.nhk.or.jp/rss/news/cat5.xml"},
    {"name": "Nikkei Asia",        "url": "https://asia.nikkei.com/rss/feed/nar"},
    {"name": "Yahoo Finance US",   "url": "https://finance.yahoo.com/news/rssindex"},
]

_MAX_PER_FEED = 5


def fetch_news(max_items: int = 10) -> list[dict]:
    """全 RSS フィードからニュースを取得。失敗したフィードはスキップする。"""
    all_items: list[dict] = []
    for feed_info in RSS_FEEDS:
        try:
            items = _fetch_feed(feed_info)
            all_items.extend(items)
        except Exception as e:
            print(f"[ERROR] {feed_info['name']} RSS取得失敗: {e}")
    return all_items[:max_items]


def _fetch_feed(feed_info: dict) -> list[dict]:
    feed = feedparser.parse(feed_info["url"])
    if not feed.entries:
        raise ValueError("エントリなし")
    return [
        {
            "title": entry.get("title", "（タイトルなし）"),
            "source": feed_info["name"],
            "url": entry.get("link", ""),
        }
        for entry in feed.entries[:_MAX_PER_FEED]
    ]
