import base64
import json
import os
from datetime import datetime

import pandas as pd
import requests
import yfinance as yf

CHART_TICKERS = {
    "日経225": {"symbol": "^N225", "key": "nikkei225", "unit": "円"},
    "VIX": {"symbol": "^VIX", "key": "vix", "unit": "Points"},
    "S&P500": {"symbol": "^GSPC", "key": "sp500", "unit": "USD"},
}

_MA_STYLES = [
    (12, "SMA 12", "rgb(255,140,0)", 1.5),
    (26, "SMA 26", "rgb(0,180,0)", 1.5),
]


def _github_config() -> tuple[str, str, str]:
    """Return (token, owner, repo). GitHub Actions can provide GITHUB_REPOSITORY."""
    token = os.environ.get("GITHUB_TOKEN", "")
    repo_full = os.environ.get("GITHUB_REPOSITORY", "")
    if repo_full and "/" in repo_full:
        owner, repo = repo_full.split("/", 1)
    else:
        owner = os.environ.get("GITHUB_OWNER", "")
        repo = os.environ.get("GITHUB_REPO", "")
    if not all([token, owner, repo]):
        raise ValueError(
            "GITHUB_TOKEN / GITHUB_OWNER / GITHUB_REPO が未設定です。"
            ".env ファイルに設定してください。"
        )
    return token, owner, repo


def fetch_ohlcv(symbol: str) -> pd.DataFrame:
    """Fetch two years of daily OHLCV data. Return an empty DataFrame on failure."""
    try:
        df = yf.Ticker(symbol).history(period="2y", interval="1d")
        return df.dropna(subset=["Open", "High", "Low", "Close"])
    except Exception:
        return pd.DataFrame()


def _add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    for period, _, _, _ in _MA_STYLES:
        df[f"SMA{period}"] = df["Close"].rolling(period).mean()
    return df


def _series_values(series: pd.Series, allow_none: bool = False) -> list[float | None]:
    values: list[float | None] = []
    for value in series:
        if pd.isna(value):
            values.append(None if allow_none else 0.0)
        else:
            values.append(float(value))
    return values


def _build_chart_html(df: pd.DataFrame, title: str, unit: str) -> str:
    """Build fullscreen candlestick chart HTML for Notion embeds."""
    dates = [d.strftime("%Y-%m-%d") for d in df.index]
    candle_data = [
        [float(row.Open), float(row.Close), float(row.Low), float(row.High)]
        for row in df.itertuples()
    ]
    ma_data = {
        f"SMA {period}": _series_values(df[f"SMA{period}"], allow_none=True)
        for period, _, _, _ in _MA_STYLES
    }
    ma_styles = [
        {"name": name, "color": color, "width": width}
        for _, name, color, width in _MA_STYLES
    ]

    title_escaped = title.replace("<", "&lt;").replace(">", "&gt;")
    js = f"""
const title = {json.dumps(title, ensure_ascii=False)};
const unit = {json.dumps(unit, ensure_ascii=False)};
const dates = {json.dumps(dates, ensure_ascii=False)};
const candles = {json.dumps(candle_data, ensure_ascii=False)};
const maData = {json.dumps(ma_data, ensure_ascii=False)};
const maStyles = {json.dumps(ma_styles, ensure_ascii=False)};
const el = id => document.getElementById(id);
const fmt = v => (v == null || isNaN(+v))
  ? '---'
  : (+v).toLocaleString('ja-JP', {{minimumFractionDigits:2, maximumFractionDigits:2}}) + ' ' + unit;

function updatePanelByIndex(idx) {{
  if (idx == null || idx < 0 || idx >= candles.length) return;
  const c = candles[idx];
  el('i-date').textContent = dates[idx] || '---';
  el('i-open').textContent = fmt(c[0]);
  el('i-close').textContent = fmt(c[1]);
  el('i-low').textContent = fmt(c[2]);
  el('i-high').textContent = fmt(c[3]);
}}

const chartEl = document.getElementById('chart');
const chart = echarts.init(chartEl, null, {{renderer: 'canvas'}});
chart.setOption({{
  animation: false,
  grid: {{left: 58, right: 18, top: 10, bottom: 28, containLabel: true}},
  xAxis: {{
    type: 'category',
    data: dates,
    boundaryGap: true,
    axisLine: {{lineStyle: {{color: '#0b2a55'}}}},
    axisLabel: {{color: '#0b2a55'}}
  }},
  yAxis: {{
    scale: true,
    name: unit,
    nameLocation: 'middle',
    nameGap: 44,
    axisLabel: {{color: '#0b2a55'}},
    splitLine: {{lineStyle: {{color: '#eef1f5'}}}}
  }},
  dataZoom: [{{type: 'inside', xAxisIndex: 0, start: 0, end: 100}}],
  tooltip: {{trigger: 'axis', showContent: false, axisPointer: {{type: 'cross'}}}},
  series: [
    {{
      name: title,
      type: 'candlestick',
      data: candles,
      itemStyle: {{
        color: '#dc3232',
        color0: '#0064c8',
        borderColor: '#dc3232',
        borderColor0: '#0064c8'
      }}
    }},
    ...maStyles.map(ma => ({{
      name: ma.name,
      type: 'line',
      data: maData[ma.name],
      smooth: true,
      symbol: 'none',
      lineStyle: {{width: ma.width, color: ma.color}}
    }}))
  ]
}});

function setRange(kind, btn) {{
  document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const end = dates.length - 1;
  const endDate = new Date(dates[end]);
  const days = {{week: 7, month1: 31, month3: 93, month6: 186, year1: 366}}[kind];
  const startDate = new Date(endDate.getTime() - days * 86400000);
  let start = dates.findIndex(d => new Date(d) >= startDate);
  if (start < 0) start = 0;
  chart.setOption({{dataZoom: [{{startValue: dates[start], endValue: dates[end]}}]}});
}}

chart.on('updateAxisPointer', event => {{
  const info = event.axesInfo && event.axesInfo[0];
  if (info) updatePanelByIndex(info.value);
}});
chart.on('click', params => updatePanelByIndex(params.dataIndex));
updatePanelByIndex(dates.length - 1);

function resizeChart() {{ chart.resize(); }}
window.addEventListener('resize', resizeChart);
new ResizeObserver(resizeChart).observe(chartEl);
requestAnimationFrame(resizeChart);
setTimeout(resizeChart, 250);
setTimeout(resizeChart, 1000);
for (const btn of document.querySelectorAll('.range-btn')) {{
  btn.addEventListener('click', () => setRange(btn.dataset.range, btn));
}}
"""

    css = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 100%; height: 100%; }
body {
  background: #fff; overflow: hidden; color: #0b2a55;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
#title {
  position: fixed; top: 6px; left: 0; right: 0; height: 28px;
  text-align: center; font-size: 18px; font-weight: 500; z-index: 2;
}
#toolbar {
  position: fixed; top: 34px; left: 0; right: 0; height: 28px;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  z-index: 2; pointer-events: none;
}
.range-btn {
  border: 0; border-radius: 4px; background: #eef0f2; color: #0b2a55;
  font-size: 12px; font-weight: 600; padding: 4px 9px; cursor: pointer;
  pointer-events: auto;
}
.range-btn.active { background: #dce6f7; }
#chart {
  position: fixed; top: 64px; left: 0; right: 0; bottom: 88px;
  width: 100%; height: calc(100vh - 152px); min-height: 260px;
}
#info-panel {
  position: fixed; bottom: 0; left: 0; right: 0; height: 88px;
  background: #f5f7fa; border-top: 1px solid #dde1e7;
  display: flex; align-items: center; justify-content: center; padding: 0 8px;
  overflow: hidden;
}
.info-cell {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 0 10px; border-right: 1px solid #dde1e7; flex-shrink: 0;
}
.info-label { font-size: 10px; color: #999; margin-bottom: 3px; white-space: nowrap; }
.info-value { font-size: 13px; font-weight: 700; white-space: nowrap; }
"""

    return (
        "<!DOCTYPE html>\n"
        '<html lang="ja">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{title_escaped}</title>\n"
        f"<style>{css}</style>\n"
        '<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>\n'
        "</head>\n"
        "<body>\n"
        f'<div id="title">{title_escaped}</div>\n'
        '<div id="toolbar">\n'
        '  <button class="range-btn" data-range="week">1週間</button>\n'
        '  <button class="range-btn" data-range="month1">1ヶ月</button>\n'
        '  <button class="range-btn" data-range="month3">3ヶ月</button>\n'
        '  <button class="range-btn" data-range="month6">6ヶ月</button>\n'
        '  <button class="range-btn active" data-range="year1">1年</button>\n'
        "</div>\n"
        '<div id="chart"></div>\n'
        '<div id="info-panel">\n'
        '  <div class="info-cell" style="border-right:none;min-width:88px;">\n'
        '    <span class="info-label">日付</span>\n'
        '    <span class="info-value" id="i-date" style="font-size:12px;color:#555">---</span>\n'
        "  </div>\n"
        '  <div class="info-cell">\n'
        '    <span class="info-label">始値</span>\n'
        '    <span class="info-value" id="i-open" style="color:#333">---</span>\n'
        "  </div>\n"
        '  <div class="info-cell">\n'
        '    <span class="info-label">高値</span>\n'
        '    <span class="info-value" id="i-high" style="color:rgb(220,50,50)">---</span>\n'
        "  </div>\n"
        '  <div class="info-cell">\n'
        '    <span class="info-label">安値</span>\n'
        '    <span class="info-value" id="i-low" style="color:rgb(0,100,200)">---</span>\n'
        "  </div>\n"
        '  <div class="info-cell">\n'
        '    <span class="info-label">終値</span>\n'
        '    <span class="info-value" id="i-close" style="color:#333">---</span>\n'
        "  </div>\n"
        "</div>\n"
        f"<script>\n{js}</script>\n"
        "</body>\n"
        "</html>\n"
    )


def _upload_html_to_github(
    html: str, filename: str, token: str, owner: str, repo: str
) -> str:
    """Create or update docs/charts/{filename} via GitHub API and return Pages URL."""
    path = f"docs/charts/{filename}"
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    existing = requests.get(api_url, headers=headers)
    sha = existing.json().get("sha") if existing.status_code == 200 else None

    payload: dict = {
        "message": f"Update chart: {filename} [skip ci]",
        "content": base64.b64encode(html.encode("utf-8")).decode("ascii"),
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(api_url, json=payload, headers=headers)
    resp.raise_for_status()
    version = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"https://{owner}.github.io/{repo}/charts/{filename}?v={version}"


def fetch_all_chart_urls() -> dict:
    result = {}
    token, owner, repo = _github_config()
    for name, info in CHART_TICKERS.items():
        try:
            df = fetch_ohlcv(info["symbol"])
            if df.empty:
                raise ValueError("データなし")
            df = _add_moving_averages(df)
            html = _build_chart_html(df, name, info["unit"])
            filename = f"{info['key']}.html"
            url = _upload_html_to_github(html, filename, token, owner, repo)
            result[name] = url
            print(f"  [チャート] {name}: OK")
        except Exception as e:
            print(f"  [WARN] チャートURL生成失敗: {name}: {e}")
            result[name] = None
    return result
