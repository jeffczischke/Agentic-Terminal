"""Renders the collected signal data into the dense terminal dashboard."""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from . import config
from .signals import _pick, _rows, _f

CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');
:root{--bg:#080B0C;--panel:#0D1214;--panel2:#111819;--line:#1E2A2C;--line2:#2A3A3D;
--txt:#C8D6D3;--dim:#6B7F80;--faint:#455658;--grn:#3FD68A;--red:#FF5A52;--amb:#F0B429;
--cyn:#3FC7D6;--mag:#B98CE8;--grnbg:#0C1F17;--redbg:#22100F;--ambbg:#1F1A0B;}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:'IBM Plex Mono',monospace;font-size:12px;
line-height:1.4;padding:10px;max-width:1600px;margin:0 auto;
background-image:repeating-linear-gradient(0deg,rgba(63,214,138,.014) 0 1px,transparent 1px 3px);}
.g{color:var(--grn)}.r{color:var(--red)}.a{color:var(--amb)}.c{color:var(--cyn)}.m{color:var(--mag)}
.d{color:var(--dim)}.f{color:var(--faint)}
.top{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;
border:1px solid var(--line2);background:var(--panel);padding:7px 11px;margin-bottom:8px}
.top .id{font-weight:700;letter-spacing:.16em;font-size:13px;color:var(--grn)}
.top .id span{color:var(--faint);font-weight:400;letter-spacing:.05em}
.top .meta{font-size:11px;color:var(--dim);display:flex;gap:16px;flex-wrap:wrap}
.blink{display:inline-block;width:7px;height:7px;background:var(--grn);border-radius:50%;
margin-right:5px;vertical-align:middle;animation:pl 2s infinite}
@keyframes pl{0%,100%{opacity:1}50%{opacity:.25}}
@media(prefers-reduced-motion:reduce){.blink{animation:none}}
.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:8px}
.p{background:var(--panel);border:1px solid var(--line);overflow:hidden}
.p>h2{font-size:10px;letter-spacing:.19em;text-transform:uppercase;color:var(--faint);
background:var(--panel2);border-bottom:1px solid var(--line);padding:5px 10px;font-weight:600;
display:flex;justify-content:space-between;align-items:center}
.p>h2 em{font-style:normal;font-size:9px;letter-spacing:.1em}
.pb{padding:9px 10px}
.s3{grid-column:span 3}.s4{grid-column:span 4}.s6{grid-column:span 6}
.s8{grid-column:span 8}.s12{grid-column:span 12}
table{width:100%;border-collapse:collapse;font-size:11.5px;font-variant-numeric:tabular-nums}
th{text-align:left;font-size:9px;letter-spacing:.13em;color:var(--faint);text-transform:uppercase;
font-weight:600;padding:5px 7px;border-bottom:1px solid var(--line2);white-space:nowrap}
td{padding:5px 7px;border-bottom:1px solid #131C1E;white-space:nowrap}
tr:last-child td{border-bottom:0}
tbody tr:hover{background:#0F1719}
.num{text-align:right}
.sym{font-weight:700;letter-spacing:.03em}
.tag{font-size:8.5px;letter-spacing:.1em;padding:1px 5px;border:1px solid;text-transform:uppercase;font-weight:600}
.t-bull{color:var(--grn);border-color:#1E5A3E;background:var(--grnbg)}
.t-bear{color:var(--red);border-color:#5A2320;background:var(--redbg)}
.t-mix{color:var(--amb);border-color:#5A4715;background:var(--ambbg)}
.lat{font-size:9px;padding:1px 4px;border:1px solid var(--line2);color:var(--dim);letter-spacing:.06em}
.lat.live{color:var(--grn);border-color:#1E5A3E}
.lat.mid{color:var(--amb);border-color:#5A4715}
.lat.slow{color:var(--red);border-color:#5A2320}
.bar{position:relative;height:5px;background:#131C1E;border:1px solid var(--line);min-width:60px}
.bar i{position:absolute;top:0;bottom:0;left:0;display:block}
.bar i.g{background:var(--grn)}.bar i.r{background:var(--red)}
.err{border:1px solid #5A2320;background:var(--redbg);padding:8px 10px;margin-bottom:8px;
font-size:11px;color:#E8B4AF}
.kvline{display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px dotted #172123;font-size:11px}
.kvline:last-child{border-bottom:0}.kvline .kk{color:var(--dim)}
ul.nt{list-style:none;font-size:11px;padding:0 10px}
ul.nt li{padding:5px 0;border-bottom:1px solid #131C1E;color:var(--dim)}
ul.nt li:last-child{border-bottom:0}ul.nt b{color:var(--txt)}
.foot{margin-top:9px;padding:7px 10px;border:1px solid var(--line);background:var(--panel);
font-size:10px;color:var(--faint);line-height:1.65}.foot b{color:var(--dim)}
.empty{padding:14px 10px;color:var(--faint);font-size:11px;text-align:center}
@media(max-width:1150px){.s3,.s4{grid-column:span 6}.s8{grid-column:span 12}}
@media(max-width:700px){.grid>*{grid-column:span 12!important}table{font-size:10.5px}
.scroll{overflow-x:auto}}
"""

LAT_CLASS = {0: "live", 1: "live", 2: "live", 45: "slow"}


def _esc(v: Any) -> str:
    return html.escape(str(v)) if v is not None else ""


def _err_of(payload: Any) -> str | None:
    if isinstance(payload, dict) and "__error__" in payload:
        return str(payload["__error__"])
    return None


def _panel(title: str, badge: str, body: str, span: str = "s6") -> str:
    return (
        f'<div class="p {span}"><h2>{title} <em>{badge}</em></h2>{body}</div>'
    )


def _table(headers: list[str], rows: list[list[str]], empty: str) -> str:
    if not rows:
        return f'<div class="empty">{_esc(empty)}</div>'
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(r) + "</tr>" for r in rows)
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def render(data: dict[str, Any], account: dict[str, Any] | None = None) -> str:
    account = account or {}
    gen = data.get("generated_at", "")
    errors = [
        f"{name}: {_err_of(data.get(name))}"
        for name in ("market_tide", "congress", "insider", "darkpool_recent", "flow_alerts", "news")
        if _err_of(data.get(name))
    ]

    err_block = ""
    if errors:
        items = "<br>".join(_esc(e) for e in errors)
        err_block = (
            f'<div class="err"><b>DEGRADED — {len(errors)} source(s) unavailable.</b><br>{items}'
            "<br><span class=\"f\">Panels below render from what did return; "
            "nothing is fabricated to fill gaps.</span></div>"
        )

    # ---- confluence ----
    conf_rows = []
    for row in data.get("confluence", [])[:15]:
        bias = row["bias"]
        cls = {"BULL": "t-bull", "BEAR": "t-bear", "MIXED": "t-mix"}[bias]
        width = min(abs(row["net"]) * 8, 100)
        color = "g" if row["net"] > 0 else "r"
        conf_rows.append(
            [
                f'<td class="sym">{_esc(row["ticker"])}</td>',
                f'<td class="num">{row["bull"]:.1f}</td>',
                f'<td class="num">{row["bear"]:.1f}</td>',
                f'<td class="num"><b class="{color}">{row["net"]:+.1f}</b></td>',
                f'<td><div class="bar"><i class="{color}" style="width:{width:.0f}%"></i></div></td>',
                f'<td class="num"><b>{row["source_count"]}</b></td>',
                f'<td class="f">{_esc(", ".join(row["sources"]))}</td>',
                f'<td><span class="tag {cls}">{bias}</span></td>',
            ]
        )
    conf_panel = _panel(
        "Confluence Ranking",
        '<span class="f">WEIGHTED BY SIGNAL LATENCY</span>',
        _table(
            ["SYM", "BULL", "BEAR", "NET", "", "SRC", "SOURCES", "BIAS"],
            conf_rows,
            "No confluence data — signal sources returned empty.",
        )
        + '<div class="pb" style="border-top:1px solid var(--line);color:var(--faint);font-size:10.5px">'
        "SRC = number of independent datasets agreeing. Breadth outranks magnitude: a 3-source "
        "signal is stronger evidence than one loud dataset. Congress weighted at 0.5 vs flow at 3.0 "
        "because of the 45-day disclosure lag.</div>",
        "s8",
    )

    # ---- latency key ----
    lat_rows = ""
    for name, days in sorted(config.SIGNAL_LATENCY.items(), key=lambda kv: kv[1]):
        cls = "live" if days <= 2 else ("mid" if days <= 10 else "slow")
        label = "same day" if days == 0 else f"T+{days}d"
        verdict = "ACTIONABLE" if days <= 2 else "CONTEXT ONLY"
        vcls = "g" if days <= 2 else "r"
        lat_rows += (
            f'<div class="kvline"><span class="kk"><span class="lat {cls}">{label}</span> '
            f"{_esc(name)}</span><span class=\"{vcls}\">{verdict}</span></div>"
        )
    lat_panel = _panel(
        "Signal Latency",
        '<span class="f">TRUST TIERS</span>',
        f'<div class="pb">{lat_rows}'
        '<div style="margin-top:8px;font-size:10.5px;color:var(--faint);line-height:1.6">'
        "Bottom tiers are idea generation, never entry triggers. Entry timing stays on "
        "price / volume / 200-DMA.</div></div>",
        "s4",
    )

    # ---- flow ----
    flow_rows = []
    for row in _rows(data.get("flow_alerts"))[:14]:
        sym = _pick(row, "ticker", "ticker_symbol", "underlying_symbol", default="?")
        prem = _f(_pick(row, "total_premium", "premium"))
        kind = str(_pick(row, "type", "option_type", default="")).upper()
        strike = _pick(row, "strike", "strike_price", default="")
        expiry = _pick(row, "expiry", "expiration", "expires", default="")
        cls = "g" if "CALL" in kind else ("r" if "PUT" in kind else "d")
        flow_rows.append(
            [
                f'<td class="sym">{_esc(sym)}</td>',
                f'<td class="{cls}">{_esc(kind or "—")}</td>',
                f'<td class="num">{_esc(strike)}</td>',
                f'<td class="f">{_esc(expiry)}</td>',
                f'<td class="num"><b>${prem:,.0f}</b></td>',
            ]
        )
    flow_panel = _panel(
        "Options Flow Alerts",
        '<span class="g">SAME DAY · ACTIONABLE</span>',
        _table(["SYM", "TYPE", "STRIKE", "EXP", "PREMIUM"], flow_rows,
               _err_of(data.get("flow_alerts")) or "No qualifying flow above premium threshold."),
    )

    # ---- dark pool ----
    dp_rows = []
    for row in _rows(data.get("darkpool_recent"))[:14]:
        sym = _pick(row, "ticker", "ticker_symbol", "symbol", default="?")
        size = _f(_pick(row, "size", "volume"))
        price = _f(_pick(row, "price"))
        notional = _f(_pick(row, "premium", "value", "notional")) or size * price
        dp_rows.append(
            [
                f'<td class="sym">{_esc(sym)}</td>',
                f'<td class="num">{size:,.0f}</td>',
                f'<td class="num">{price:,.2f}</td>',
                f'<td class="num"><b class="c">${notional:,.0f}</b></td>',
            ]
        )
    dp_panel = _panel(
        "Dark Pool Prints",
        '<span class="g">SAME DAY · INSTITUTIONAL</span>',
        _table(["SYM", "SIZE", "PRICE", "NOTIONAL"], dp_rows,
               _err_of(data.get("darkpool_recent")) or "No dark pool prints returned."),
    )

    # ---- insider ----
    ins_rows = []
    for row in _rows(data.get("insider"))[:12]:
        sym = _pick(row, "ticker", "ticker_symbol", "symbol", default="?")
        who = _pick(row, "owner_name", "insider_name", "reporting_name", default="—")
        action = str(_pick(row, "transaction_type", "transaction_code", "type", default="—"))
        value = _f(_pick(row, "value", "transaction_value", "amount"))
        buy = any(k in action.lower() for k in ("buy", "purchase", "p-", "acquire"))
        cls = "g" if buy else "r"
        ins_rows.append(
            [
                f'<td class="sym">{_esc(sym)}</td>',
                f'<td class="f">{_esc(str(who)[:26])}</td>',
                f'<td class="{cls}">{_esc(action[:14])}</td>',
                f'<td class="num">${value:,.0f}</td>',
            ]
        )
    ins_panel = _panel(
        "Insider Transactions",
        '<span class="g">T+2 · FORM 4</span>',
        _table(["SYM", "INSIDER", "ACTION", "VALUE"], ins_rows,
               _err_of(data.get("insider")) or "No insider transactions returned."),
    )

    # ---- congress ----
    cong_rows = []
    for row in _rows(data.get("congress"))[:12]:
        sym = _pick(row, "ticker", "ticker_symbol", "symbol", default="?")
        who = _pick(row, "name", "representative", "member", default="—")
        action = str(_pick(row, "transaction", "type", default="—"))
        amount = _pick(row, "amount", "range", "size", default="—")
        tdate = _pick(row, "transaction_date", "traded", default="")
        rdate = _pick(row, "report_date", "filed", "disclosed_at", default="")
        buy = "purchase" in action.lower() or "buy" in action.lower()
        cls = "g" if buy else "r"
        cong_rows.append(
            [
                f'<td class="sym">{_esc(sym)}</td>',
                f'<td class="f">{_esc(str(who)[:22])}</td>',
                f'<td class="{cls}">{_esc(action[:10])}</td>',
                f'<td class="num f">{_esc(amount)}</td>',
                f'<td class="f">{_esc(tdate)}</td>',
                f'<td class="f">{_esc(rdate)}</td>',
            ]
        )
    cong_panel = _panel(
        "Congressional Disclosures",
        '<span class="r">T+45d LAG · CONTEXT ONLY</span>',
        _table(["SYM", "MEMBER", "ACTION", "RANGE", "TRADED", "FILED"], cong_rows,
               _err_of(data.get("congress")) or "No congressional trades returned.")
        + '<div class="pb" style="border-top:1px solid var(--line);color:var(--faint);font-size:10.5px">'
        "Compare TRADED vs FILED — the gap is how stale the signal is. STOCK Act allows up to 45 days.</div>",
    )

    # ---- news ----
    news_items = ""
    nrows = _rows(data.get("news"))[:10]
    if nrows:
        for row in nrows:
            headline = _pick(row, "headline", "title", "text", default="")
            src = _pick(row, "source", "publisher", default="")
            ts = _pick(row, "created_at", "timestamp", "published_at", default="")
            news_items += (
                f"<li><b>{_esc(str(headline)[:160])}</b> "
                f'<span class="f">{_esc(src)} {_esc(str(ts)[:16])}</span></li>'
            )
    else:
        news_items = f'<li class="f">{_esc(_err_of(data.get("news")) or "No headlines returned.")}</li>'
    # news_panel is assembled with the other layout panels below (bottom row).

    # ---- market tide ----
    tide = data.get("market_tide")
    tide_body = ""
    trows = _rows(tide)
    if trows:
        last = trows[-1]
        ncp = _f(_pick(last, "net_call_premium"))
        npp = _f(_pick(last, "net_put_premium"))
        net = ncp - npp
        bias = "RISK-ON" if net > 0 else "RISK-OFF"
        cls = "g" if net > 0 else "r"
        tide_body = (
            f'<div class="pb">'
            f'<div class="kvline"><span class="kk">Net call premium</span><span class="g">${ncp:,.0f}</span></div>'
            f'<div class="kvline"><span class="kk">Net put premium</span><span class="r">${npp:,.0f}</span></div>'
            f'<div class="kvline"><span class="kk">Differential</span><span class="{cls}">${net:,.0f}</span></div>'
            f'<div class="kvline"><span class="kk">Read</span><span class="{cls}"><b>{bias}</b></span></div>'
            f'<div style="margin-top:8px;font-size:10.5px;color:var(--faint)">'
            f"Market Tide is a live sentiment gauge built from net options premium — a direct "
            f"read rather than the VIX proxy it replaces.</div></div>"
        )
    else:
        tide_body = f'<div class="empty">{_esc(_err_of(tide) or "Market tide unavailable.")}</div>'
    tide_panel = _panel("Market Tide", '<span class="g">LIVE SENTIMENT</span>', tide_body, "s4")

    # ---- per-ticker technicals ----
    tech_rows = []
    for sym, entry in (data.get("tickers") or {}).items():
        sma = entry.get("sma200")
        rsi = entry.get("rsi14")
        sma_v = _latest_indicator(sma)
        rsi_v = _latest_indicator(rsi)
        dp_n = len(_rows(entry.get("darkpool")))
        fl_n = len(_rows(entry.get("flow")))
        rsi_cls = "a" if rsi_v and (rsi_v < 35 or rsi_v > 70) else "d"
        tech_rows.append(
            [
                f'<td class="sym">{_esc(sym)}</td>',
                f'<td class="num">{sma_v:,.2f}</td>' if sma_v else '<td class="num f">—</td>',
                f'<td class="num {rsi_cls}">{rsi_v:.1f}</td>' if rsi_v else '<td class="num f">—</td>',
                f'<td class="num">{dp_n}</td>',
                f'<td class="num">{fl_n}</td>',
            ]
        )
    tech_panel = _panel(
        "Focus Technicals",
        '<span class="f">200DMA · RSI · EVENT COUNTS</span>',
        _table(["SYM", "200DMA", "RSI14", "DP", "FLOW"], tech_rows, "No focus data."),
        "s4",
    )

    # ---- equity positions (live from Robinhood via MCP) ----
    # Read-only account context. This panel never triggers an order; execution
    # stays in the brokerage with explicit per-order human confirmation.
    equity = data.get("equity")
    eq_err = _err_of(equity)
    if not eq_err and isinstance(equity, dict) and _rows(equity.get("positions")):
        pos_rows = []
        for p in _rows(equity.get("positions")):
            sym = _pick(p, "symbol", "ticker", default="?")
            qty = _f(_pick(p, "quantity", "shares"))
            avg = _f(_pick(p, "average_buy_price", "avg_cost"))
            last = _f(_pick(p, "last_price", "price"))
            prev = _f(_pick(p, "previous_close", "prev_close"), default=last)
            mkt = qty * last
            cost = qty * avg
            upnl = mkt - cost
            upnl_pct = (upnl / cost * 100) if cost else 0.0
            day = qty * (last - prev)
            pcls = "g" if upnl >= 0 else "r"
            dcls = "g" if day >= 0 else "r"
            pos_rows.append(
                [
                    f'<td class="sym">{_esc(sym)}</td>',
                    f'<td class="num">{qty:,.4f}</td>',
                    f'<td class="num">{avg:,.2f}</td>',
                    f'<td class="num">{last:,.2f}</td>',
                    f'<td class="num"><b>${mkt:,.2f}</b></td>',
                    f'<td class="num {pcls}"><b>{upnl:+,.2f}</b> <span class="f">{upnl_pct:+.1f}%</span></td>',
                    f'<td class="num {dcls}">{day:+,.2f}</td>',
                ]
            )
        tv = _f(equity.get("total_value"))
        cash = _f(equity.get("cash"))
        bp = _f(equity.get("buying_power"))
        summary = (
            '<div class="pb" style="border-bottom:1px solid var(--line)">'
            f'<div class="kvline"><span class="kk">Account value</span><span><b>${tv:,.2f}</b></span></div>'
            f'<div class="kvline"><span class="kk">Cash</span><span class="c">${cash:,.2f}</span></div>'
            f'<div class="kvline"><span class="kk">Buying power</span><span class="c">${bp:,.2f}</span></div>'
            "</div>"
        )
        eq_body = summary + _table(
            ["SYM", "QTY", "AVG", "LAST", "MKT VAL", "UNREAL P&L", "DAY"],
            pos_rows,
            "No open equity positions.",
        )
    else:
        eq_body = f'<div class="empty">{_esc(eq_err or "No Robinhood positions loaded.")}</div>'
    nick = equity.get("nickname") if isinstance(equity, dict) else None
    eq_panel = _panel(
        "Equity Positions",
        f'<span class="g">LIVE · ROBINHOOD{(" · " + _esc(nick)) if nick else ""}</span>',
        eq_body,
        "s8",
    )

    news_panel = _panel("Catalyst Tape", '<span class="g">LIVE</span>',
                        f'<ul class="nt">{news_items}</ul>', "s8")

    # Grid packs to 12 cols per row: [conf8+lat4] [flow6+dp6] [ins6+cong6]
    # [eq8+tide4] [tech4+news8].
    body = "".join(
        [
            conf_panel, lat_panel,
            flow_panel, dp_panel,
            ins_panel, cong_panel,
            eq_panel, tide_panel,
            tech_panel, news_panel,
        ]
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AGENTIC // TERMINAL</title><style>{CSS}</style></head><body>
<div class="top">
  <div class="id"><span class="blink"></span>AGENTIC//TERMINAL
    <span>· RH #{_esc(config.ACCOUNT_NUMBER)} · CASH</span></div>
  <div class="meta">
    <span>GEN {_esc(gen)}</span>
    <span>SOURCE <b class="c">UNUSUAL WHALES REST</b></span>
    <span>FOCUS {_esc(", ".join(data.get("focus", [])))}</span>
    <span class="f">SNAPSHOT — NOT LIVE-POLLING</span>
  </div>
</div>
{err_block}
<div class="grid">{body}</div>
<div class="foot">
  <b>NO ORDERS PLACED.</b> This tool is read-only — it never touches the brokerage.
  Trading stays in Robinhood MCP with explicit per-order confirmation.
  &nbsp;·&nbsp; Signals weighted by latency; congressional and 13F data lag up to 45 days and are
  context, never entry triggers. &nbsp;·&nbsp; Empty panels mean the source returned nothing —
  no placeholder data is invented. &nbsp;·&nbsp; Not financial advice.
</div>
</body></html>"""


def _latest_indicator(payload: Any) -> float | None:
    rows = _rows(payload)
    if not rows:
        return None
    last = rows[-1]
    for key in ("value", "sma", "rsi", "close", "indicator"):
        if key in last:
            val = _f(last[key], default=float("nan"))
            if val == val:  # not NaN
                return val
    return None


def write(data: dict[str, Any], out_dir: Path | None = None) -> Path:
    out_dir = out_dir or config.OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    html_path = out_dir / f"terminal-{stamp}.html"
    html_path.write_text(render(data), encoding="utf-8")
    (out_dir / f"snapshot-{stamp}.json").write_text(
        json.dumps(data, indent=2, default=str), encoding="utf-8"
    )
    return html_path
