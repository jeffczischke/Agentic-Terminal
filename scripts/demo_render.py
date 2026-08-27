"""Render the dashboard with clearly-labelled SAMPLE data for design iteration.

This does NOT hit Unusual Whales and is NOT a real scan. Every row here is
synthetic and the output carries a DEMO watermark. It exists only so the
layout can be reviewed without a live API key.
"""

from __future__ import annotations

from pathlib import Path

from agentic import dashboard
from agentic.signals import score_confluence

# --- synthetic source payloads (shapes match what uw_client returns) ---
flow_alerts = [
    {"ticker": "NVDA", "type": "CALL", "strike": 145, "expiry": "2026-09-19", "total_premium": 2_450_000},
    {"ticker": "AVGO", "type": "CALL", "strike": 180, "expiry": "2026-09-19", "total_premium": 1_180_000},
    {"ticker": "PLTR", "type": "CALL", "strike": 42, "expiry": "2026-10-17", "total_premium": 890_000},
    {"ticker": "AMD", "type": "PUT", "strike": 155, "expiry": "2026-09-19", "total_premium": 640_000},
    {"ticker": "MRVL", "type": "CALL", "strike": 95, "expiry": "2026-09-19", "total_premium": 520_000},
    {"ticker": "WFC", "type": "CALL", "strike": 72, "expiry": "2026-11-21", "total_premium": 410_000},
    {"ticker": "TSLA", "type": "PUT", "strike": 300, "expiry": "2026-09-19", "total_premium": 305_000},
]

darkpool_recent = [
    {"ticker": "NVDA", "size": 420_000, "price": 141.20, "premium": 59_304_000},
    {"ticker": "AVGO", "size": 88_000, "price": 176.40, "premium": 15_523_000},
    {"ticker": "PLTR", "size": 640_000, "price": 39.85, "premium": 25_504_000},
    {"ticker": "WFC", "size": 210_000, "price": 70.10, "premium": 14_721_000},
    {"ticker": "AMD", "size": 150_000, "price": 152.30, "premium": 22_845_000},
]

insider = [
    {"ticker": "WFC", "owner_name": "Scharf Charles W", "transaction_type": "Purchase", "value": 1_950_000},
    {"ticker": "PLTR", "owner_name": "Karp Alexander C", "transaction_type": "Sale", "value": 8_400_000},
    {"ticker": "MRVL", "owner_name": "Murphy Matthew J", "transaction_type": "Purchase", "value": 720_000},
]

congress = [
    {"ticker": "NVDA", "name": "Rep. Example A.", "transaction": "Purchase", "amount": "$50K–$100K",
     "transaction_date": "2026-07-10", "report_date": "2026-08-22"},
    {"ticker": "AVGO", "name": "Sen. Example B.", "transaction": "Purchase", "amount": "$15K–$50K",
     "transaction_date": "2026-07-01", "report_date": "2026-08-14"},
    {"ticker": "AMD", "name": "Rep. Example C.", "transaction": "Sale", "amount": "$1K–$15K",
     "transaction_date": "2026-06-28", "report_date": "2026-08-11"},
]

news = [
    {"headline": "Chip demand commentary lifts semis into the print", "source": "Newswire", "created_at": "2026-08-27T13:40"},
    {"headline": "Data-center capex guidance raised across hyperscalers", "source": "MarketDesk", "created_at": "2026-08-27T12:05"},
    {"headline": "Regional banks catch a bid on rate-path repricing", "source": "Tape", "created_at": "2026-08-27T10:22"},
]

market_tide = [
    {"net_call_premium": 1_820_000_000, "net_put_premium": 1_240_000_000},
]

tickers = {
    "NVDA": {"sma200": [{"value": 118.44}], "rsi14": [{"value": 61.2}],
             "darkpool": darkpool_recent[:1], "flow": flow_alerts[:1]},
    "AVGO": {"sma200": [{"value": 162.10}], "rsi14": [{"value": 57.8}],
             "darkpool": darkpool_recent[1:2], "flow": flow_alerts[1:2]},
    "AMD":  {"sma200": [{"value": 158.90}], "rsi14": [{"value": 33.1}],
             "darkpool": darkpool_recent[4:5], "flow": flow_alerts[3:4]},
    "MRVL": {"sma200": [{"value": 82.35}], "rsi14": [{"value": 66.4}],
             "darkpool": [], "flow": flow_alerts[4:5]},
    "PLTR": {"sma200": [{"value": 34.70}], "rsi14": [{"value": 72.9}],
             "darkpool": darkpool_recent[2:3], "flow": flow_alerts[2:3]},
    "WFC":  {"sma200": [{"value": 65.20}], "rsi14": [{"value": 54.0}],
             "darkpool": darkpool_recent[3:4], "flow": flow_alerts[5:6]},
}

data = {
    "generated_at": "SAMPLE DATA — NOT A LIVE SCAN",
    "focus": ["NVDA", "AVGO", "AMD", "MRVL", "PLTR", "WFC"],
    "errors": [],
    "market_tide": market_tide,
    "congress": congress,
    "insider": insider,
    "darkpool_recent": darkpool_recent,
    "flow_alerts": flow_alerts,
    "news": news,
    "tickers": tickers,
}
data["confluence"] = score_confluence(data)

html_out = dashboard.render(data)

# Unmistakable DEMO watermark so this preview is never read as real signals.
banner = (
    '<div style="background:#22100F;border:1px solid #5A2320;color:#F0B429;'
    'padding:8px 11px;margin-bottom:8px;font-family:monospace;font-size:12px;'
    'letter-spacing:.08em;text-align:center">'
    '⚠ DEMO PREVIEW — synthetic sample data for layout review only. '
    'Not connected to Unusual Whales. No real signals.</div>'
)
html_out = html_out.replace("<body>", "<body>\n" + banner, 1)

out = Path("/tmp/claude-0/-home-user-Agentic-Terminal/600ea754-d6f2-5d4b-b667-18d172770339/scratchpad/agentic-dashboard-demo.html")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html_out, encoding="utf-8")
print(f"wrote {out} ({len(html_out):,} bytes)")
print("confluence rows:", len(data["confluence"]))
for r in data["confluence"][:6]:
    print(f"  {r['ticker']:<5} net {r['net']:+6.2f}  {r['source_count']} src  {r['bias']}  ({', '.join(r['sources'])})")
