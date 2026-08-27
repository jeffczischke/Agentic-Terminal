"""
Signal aggregation.

Pulls each UW dataset, normalises it, and scores confluence. The scoring
deliberately weights signals by how stale they are: same-day options flow and
dark pool prints can inform an entry, a 45-day-old congressional disclosure
cannot. See config.SIGNAL_LATENCY.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from . import config
from .uw_client import UWClient, UWError

log = logging.getLogger(__name__)

# Weight by actionability. Same-day institutional footprint outranks
# disclosure filings that describe trades from over a month ago.
WEIGHTS = {
    "flow": 3.0,
    "darkpool": 2.5,
    "insider": 2.0,
    "institutional": 1.0,
    "congress": 0.5,
}


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _rows(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("data", "results", "trades", "transactions"):
            inner = payload.get(key)
            if isinstance(inner, list):
                return [r for r in inner if isinstance(r, dict)]
    return []


def _pick(row: dict, *names: str, default: Any = None) -> Any:
    """UW field names vary across datasets; take the first key that exists."""
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return default


def safe(label: str, fn, *args, **kwargs) -> Any:
    """Run a fetch, converting failures into an empty result plus a warning.

    One dead endpoint should degrade a panel, not kill the whole scan.
    """
    try:
        return fn(*args, **kwargs)
    except UWError as exc:
        log.warning("%s unavailable: %s", label, exc.diagnosis)
        return {"__error__": exc.diagnosis}
    except Exception as exc:  # noqa: BLE001
        log.warning("%s failed: %s", label, exc)
        return {"__error__": str(exc)}


def collect(client: UWClient, focus: list[str]) -> dict[str, Any]:
    """Pull every signal layer. Returns a dict the dashboard renders directly."""
    out: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "focus": focus,
        "errors": [],
    }

    out["market_tide"] = safe("market tide", client.market_tide)
    out["congress"] = safe("congress", client.congress_trades, limit=60)
    out["insider"] = safe("insider", client.insider_transactions, limit=60)
    out["darkpool_recent"] = safe("dark pool", client.darkpool_recent, limit=80)
    out["flow_alerts"] = safe("flow alerts", client.flow_alerts, min_premium=100_000, limit=60)
    out["news"] = safe("news", client.news_headlines, limit=30)

    per_ticker: dict[str, dict] = {}
    for sym in focus:
        entry: dict[str, Any] = {}
        entry["darkpool"] = safe(f"darkpool {sym}", client.darkpool_ticker, sym, limit=25)
        entry["flow"] = safe(f"flow {sym}", client.flow_alerts, ticker=sym, limit=25)
        entry["options_volume"] = safe(f"opt vol {sym}", client.options_volume, sym)
        entry["sma200"] = safe(
            f"sma200 {sym}", client.technical_indicator, sym, "SMA", "daily", 200
        )
        entry["rsi14"] = safe(
            f"rsi {sym}", client.technical_indicator, sym, "RSI", "daily", 14
        )
        per_ticker[sym] = entry
    out["tickers"] = per_ticker

    out["confluence"] = score_confluence(out)
    return out


def score_confluence(data: dict[str, Any]) -> list[dict]:
    """Rank tickers by weighted agreement across independent signal sources.

    A name scoring high because three *different* datasets point the same way
    is meaningfully stronger than one scoring high on a single loud dataset,
    so we track contributing sources and surface the count.
    """
    bull: dict[str, float] = defaultdict(float)
    bear: dict[str, float] = defaultdict(float)
    sources: dict[str, set[str]] = defaultdict(set)

    # --- options flow ---
    for row in _rows(data.get("flow_alerts")):
        sym = _pick(row, "ticker", "ticker_symbol", "underlying_symbol")
        if not sym:
            continue
        premium = _f(_pick(row, "total_premium", "premium"))
        if premium <= 0:
            continue
        weight = WEIGHTS["flow"] * min(premium / 1_000_000, 3.0)
        kind = str(_pick(row, "type", "option_type", default="")).lower()
        is_call = "call" in kind or bool(row.get("is_call"))
        is_put = "put" in kind or bool(row.get("is_put"))
        if is_call:
            bull[sym] += weight
            sources[sym].add("flow")
        elif is_put:
            bear[sym] += weight
            sources[sym].add("flow")

    # --- insider transactions ---
    for row in _rows(data.get("insider")):
        sym = _pick(row, "ticker", "ticker_symbol", "symbol")
        if not sym:
            continue
        action = str(_pick(row, "transaction_type", "transaction_code", "type", default="")).lower()
        value = abs(_f(_pick(row, "value", "transaction_value", "amount")))
        weight = WEIGHTS["insider"] * min(max(value, 1) / 1_000_000, 3.0)
        if any(k in action for k in ("buy", "purchase", "p-", "acquire")):
            bull[sym] += weight
            sources[sym].add("insider")
        elif any(k in action for k in ("sell", "sale", "s-", "dispose")):
            # Insider selling is far weaker evidence than buying — executives
            # sell for liquidity, diversification, and scheduled 10b5-1 plans.
            bear[sym] += weight * 0.4
            sources[sym].add("insider")

    # --- congressional disclosures (heavily discounted for staleness) ---
    for row in _rows(data.get("congress")):
        sym = _pick(row, "ticker", "ticker_symbol", "symbol")
        if not sym:
            continue
        action = str(_pick(row, "transaction", "type", default="")).lower()
        if "purchase" in action or "buy" in action:
            bull[sym] += WEIGHTS["congress"]
            sources[sym].add("congress")
        elif "sale" in action or "sell" in action:
            bear[sym] += WEIGHTS["congress"] * 0.5
            sources[sym].add("congress")

    # --- dark pool prints ---
    for row in _rows(data.get("darkpool_recent")):
        sym = _pick(row, "ticker", "ticker_symbol", "symbol")
        if not sym:
            continue
        notional = _f(_pick(row, "premium", "value", "notional"))
        if notional <= 0:
            size = _f(_pick(row, "size", "volume"))
            notional = size * _f(_pick(row, "price"))
        if notional > 0:
            # Dark pool prints are direction-agnostic on their own; they mark
            # institutional interest, so they amplify rather than pick a side.
            bull[sym] += WEIGHTS["darkpool"] * min(notional / 10_000_000, 2.0) * 0.5
            sources[sym].add("darkpool")

    ranked = []
    for sym in set(bull) | set(bear):
        net = bull[sym] - bear[sym]
        srcs = sorted(sources[sym])
        ranked.append(
            {
                "ticker": sym,
                "bull": round(bull[sym], 2),
                "bear": round(bear[sym], 2),
                "net": round(net, 2),
                "sources": srcs,
                "source_count": len(srcs),
                "bias": "BULL" if net > 0.5 else ("BEAR" if net < -0.5 else "MIXED"),
            }
        )

    # Sort by breadth of agreement first, then magnitude. A 3-source signal
    # beats a louder 1-source signal.
    ranked.sort(key=lambda r: (r["source_count"], abs(r["net"])), reverse=True)
    return ranked[:25]
