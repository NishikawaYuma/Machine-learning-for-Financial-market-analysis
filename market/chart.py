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

_RSI_STYLES = [
    (12, "RSI 短期", "rgb(0,160,80)", 1.5),
    (26, "RSI 長期", "rgb(160,200,0)", 1.5),
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
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    for period, _, _, _ in _RSI_STYLES:
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss
        df[f"RSI{period}"] = 100 - (100 / (1 + rs))
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
    rsi_data = {
        name: _series_values(df[f"RSI{period}"], allow_none=True)
        for period, name, _, _ in _RSI_STYLES
    }
    rsi_styles = [
        {"name": name, "color": color, "width": width}
        for _, name, color, width in _RSI_STYLES
    ]
    volume_series = (
        df["Volume"]
        if "Volume" in df.columns
        else pd.Series([0] * len(df), index=df.index)
    )
    volume_data = _series_values(volume_series, allow_none=False)

    title_escaped = ""
    js = f"""
const title = {json.dumps(title, ensure_ascii=False)};
const unit = {json.dumps(unit, ensure_ascii=False)};
const dates = {json.dumps(dates, ensure_ascii=False)};
const candles = {json.dumps(candle_data, ensure_ascii=False)};
const maData = {json.dumps(ma_data, ensure_ascii=False)};
const maStyles = {json.dumps(ma_styles, ensure_ascii=False)};
const volumes = {json.dumps(volume_data, ensure_ascii=False)};
const rsiData = {json.dumps(rsi_data, ensure_ascii=False)};
const rsiStyles = {json.dumps(rsi_styles, ensure_ascii=False)};
const el = id => document.getElementById(id);
const fmtValue = v => (v == null || isNaN(+v))
  ? '---'
  : (+v).toLocaleString('ja-JP', {{minimumFractionDigits:2, maximumFractionDigits:2}});
const fmt = v => fmtValue(v) + (fmtValue(v) === '---' ? '' : ' ' + unit);
const fmtVolume = v => (v == null || isNaN(+v))
  ? '---'
  : (+v).toLocaleString('ja-JP', {{maximumFractionDigits:0}});
const indicators = {{volume: false, rsi: false}};

function updatePanelByIndex(idx) {{
  if (idx == null || idx < 0 || idx >= candles.length) return;
  const c = candles[idx];
  el('i-date').textContent = dates[idx] || '---';
  el('i-open').textContent = fmtValue(c[0]);
  el('i-close').textContent = fmtValue(c[1]);
  el('i-low').textContent = fmtValue(c[2]);
  el('i-high').textContent = fmtValue(c[3]);
  el('i-volume').textContent = fmtVolume(volumes[idx]);
  for (const style of rsiStyles) {{
    const node = el(style.name === 'RSI 短期' ? 'i-rsi-short' : 'i-rsi-long');
    node.textContent = fmtValue(rsiData[style.name][idx]);
  }}
}}

const chartEl = document.getElementById('chart');
const chart = echarts.init(chartEl, null, {{renderer: 'canvas'}});

function axisCommon(gridIndex, showLabel) {{
  return {{
    type: 'category',
    gridIndex,
    data: dates,
    boundaryGap: true,
    axisLine: {{lineStyle: {{color: '#b8c1cc'}}}},
    axisTick: {{show: false}},
    axisLabel: {{show: showLabel, color: '#333'}}
  }};
}}

function renderChart() {{
  const panelCount = Number(indicators.volume) + Number(indicators.rsi);
  const top = 66;
  const bottom = 10;
  const gap = 8;
  const panelHeight = panelCount ? 76 : 0;
  const priceBottom = bottom + panelCount * panelHeight + Math.max(0, panelCount - 1) * gap;
  const grids = [
    {{left: 58, right: 42, top, bottom: priceBottom, containLabel: true}}
  ];
  const xAxis = [axisCommon(0, panelCount === 0)];
  const yAxis = [{{
    gridIndex: 0,
    scale: true,
    name: unit,
    nameLocation: 'middle',
    nameGap: 42,
    axisLabel: {{color: '#333'}},
    splitLine: {{lineStyle: {{color: '#e5e8ec'}}}}
  }}];
  const series = [
    {{
      name: title,
      type: 'candlestick',
      xAxisIndex: 0,
      yAxisIndex: 0,
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
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: maData[ma.name],
      smooth: true,
      symbol: 'none',
      lineStyle: {{width: ma.width, color: ma.color}}
    }}))
  ];

  let nextGrid = 1;
  let nextBottom = bottom + (panelCount - 1) * (panelHeight + gap);
  if (indicators.volume) {{
    grids.push({{left: 58, right: 42, height: panelHeight, bottom: nextBottom, containLabel: true}});
    xAxis.push(axisCommon(nextGrid, !indicators.rsi));
    yAxis.push({{
      gridIndex: nextGrid,
      scale: true,
      axisLabel: {{color: '#555'}},
      splitLine: {{lineStyle: {{color: '#eef1f5'}}}}
    }});
    series.push({{
      name: '出来高',
      type: 'bar',
      xAxisIndex: nextGrid,
      yAxisIndex: nextGrid,
      data: volumes,
      itemStyle: {{color: '#8a8a8a'}},
      barWidth: '60%'
    }});
    nextGrid += 1;
    nextBottom -= panelHeight + gap;
  }}
  if (indicators.rsi) {{
    grids.push({{left: 58, right: 42, height: panelHeight, bottom: nextBottom, containLabel: true}});
    xAxis.push(axisCommon(nextGrid, true));
    yAxis.push({{
      gridIndex: nextGrid,
      min: 0,
      max: 100,
      axisLabel: {{color: '#555'}},
      splitLine: {{lineStyle: {{color: '#eef1f5'}}}}
    }});
    for (const rsi of rsiStyles) {{
      series.push({{
        name: rsi.name,
        type: 'line',
        xAxisIndex: nextGrid,
        yAxisIndex: nextGrid,
        data: rsiData[rsi.name],
        smooth: true,
        symbol: 'none',
        lineStyle: {{width: rsi.width, color: rsi.color}}
      }});
    }}
  }}

  chart.setOption({{
    animation: false,
    grid: grids,
    xAxis,
    yAxis,
    dataZoom: [{{type: 'inside', xAxisIndex: xAxis.map((_, i) => i), start: 0, end: 100}}],
    tooltip: {{trigger: 'axis', showContent: false, axisPointer: {{type: 'cross'}}}},
    series
  }}, true);
}}

renderChart();

function setRange(kind, btn) {{
  document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const end = dates.length - 1;
  const endDate = new Date(dates[end]);
  const days = {{week: 7, month1: 31, month3: 93, month6: 186, year1: 366}}[kind];
  const startDate = new Date(endDate.getTime() - days * 86400000);
  let start = dates.findIndex(d => new Date(d) >= startDate);
  if (start < 0) start = 0;
  const axisCount = chart.getOption().xAxis.length;
  chart.setOption({{dataZoom: [{{
    xAxisIndex: Array.from({{length: axisCount}}, (_, i) => i),
    startValue: dates[start],
    endValue: dates[end]
  }}]}});
}}

function toggleIndicator(kind, btn) {{
  indicators[kind] = !indicators[kind];
  btn.classList.toggle('active', indicators[kind]);
  el(kind + '-readout').classList.toggle('active', indicators[kind]);
  renderChart();
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
for (const btn of document.querySelectorAll('.indicator-btn')) {{
  btn.addEventListener('click', () => toggleIndicator(btn.dataset.indicator, btn));
}}
"""

    css = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 100%; height: 100%; }
body {
  background: #fff; overflow: hidden; color: #0b2a55;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
#toolbar {
  position: fixed; top: 32px; left: 0; right: 0; height: 30px;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  z-index: 2; pointer-events: none;
}
.range-btn, .indicator-btn {
  border: 0; border-radius: 4px; background: #eef0f2; color: #0b2a55;
  font-size: 11px; font-weight: 600; padding: 4px 8px; cursor: pointer;
  pointer-events: auto;
  box-shadow: 0 1px 3px rgba(11,42,85,0.12);
}
.range-btn.active, .indicator-btn.active { background: #dce6f7; }
.toolbar-sep { width: 1px; height: 18px; background: #d5dce5; margin: 0 2px; }
#chart {
  position: fixed; inset: 0;
  width: 100%; height: 100vh; min-height: 300px;
}
#info-panel {
  position: fixed; top: 0; left: 0; right: 0; height: 30px;
  background: rgba(255,255,255,0.94); border-bottom: 1px solid #dde1e7;
  display: flex; align-items: center; justify-content: center; gap: 12px; padding: 0 8px;
  overflow: hidden;
  z-index: 2;
}
.info-cell {
  display: flex; align-items: baseline; justify-content: center; gap: 3px;
  min-width: 0; white-space: nowrap;
}
.info-label { font-size: 11px; color: #555; font-weight: 700; white-space: nowrap; }
.info-value { font-size: 12px; font-weight: 700; white-space: nowrap; }
#i-date { color: #555; font-size: 11px; font-weight: 600; }
#indicator-panel {
  position: fixed; top: 68px; left: 8px; z-index: 2;
  display: flex; flex-direction: column; gap: 4px; pointer-events: none;
}
.indicator-readout {
  display: none; background: rgba(255,255,255,0.82); padding: 5px 7px;
  min-width: 84px; color: #333; font-size: 11px; line-height: 1.25;
}
.indicator-readout.active { display: block; }
.indicator-title { font-size: 12px; font-weight: 700; color: #333; margin-bottom: 2px; }
.indicator-row { display: flex; justify-content: space-between; gap: 10px; }
.volume-color { color: #666; }
.rsi-short { color: rgb(0,160,80); }
.rsi-long { color: rgb(160,200,0); }
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
        '<div id="info-panel">\n'
        '  <div class="info-cell"><span class="info-label">日</span><span class="info-value" id="i-date">---</span></div>\n'
        '  <div class="info-cell"><span class="info-label">始</span><span class="info-value" id="i-open">---</span></div>\n'
        '  <div class="info-cell"><span class="info-label">高</span><span class="info-value" id="i-high" style="color:rgb(220,50,50)">---</span></div>\n'
        '  <div class="info-cell"><span class="info-label">安</span><span class="info-value" id="i-low" style="color:rgb(0,100,200)">---</span></div>\n'
        '  <div class="info-cell"><span class="info-label">終</span><span class="info-value" id="i-close">---</span></div>\n'
        "</div>\n"
        '<div id="toolbar">\n'
        '  <button class="range-btn" data-range="week">1週間</button>\n'
        '  <button class="range-btn" data-range="month1">1ヶ月</button>\n'
        '  <button class="range-btn" data-range="month3">3ヶ月</button>\n'
        '  <button class="range-btn" data-range="month6">6ヶ月</button>\n'
        '  <button class="range-btn active" data-range="year1">1年</button>\n'
        '  <span class="toolbar-sep"></span>\n'
        '  <button class="indicator-btn" data-indicator="volume">出来高</button>\n'
        '  <button class="indicator-btn" data-indicator="rsi">RSI</button>\n'
        "</div>\n"
        '<div id="chart"></div>\n'
        '<div id="indicator-panel">\n'
        '  <div id="volume-readout" class="indicator-readout">\n'
        '    <div class="indicator-title">出来高</div>\n'
        '    <div class="indicator-row"><span>出来高</span><span id="i-volume" class="volume-color">---</span></div>\n'
        "  </div>\n"
        '  <div id="rsi-readout" class="indicator-readout">\n'
        '    <div class="indicator-title">RSI</div>\n'
        '    <div class="indicator-row"><span class="rsi-short">短期</span><span id="i-rsi-short">---</span></div>\n'
        '    <div class="indicator-row"><span class="rsi-long">長期</span><span id="i-rsi-long">---</span></div>\n'
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
    commit_sha = resp.json().get("commit", {}).get("sha", "unknown")
    pages_url = f"https://{owner}.github.io/{repo}/charts/{filename}"
    print(f"  [GitHub] コミット: {commit_sha[:7]} | Pages URL: {pages_url}")
    version = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{pages_url}?v={version}"


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
            version = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{info['key']}_{version}.html"
            url = _upload_html_to_github(html, filename, token, owner, repo)
            result[name] = url
            print(f"  [チャート] {name}: アップロードOK → {url}")
        except Exception as e:
            print(f"  [WARN] チャートURL生成失敗: {name}: {e}")
            result[name] = None
    return result
