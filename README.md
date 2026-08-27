# Agentic Terminal

Multi-source market signal aggregation for a discretionary swing-trading workflow.
Pulls options flow, dark pool prints, insider Form 4s, congressional disclosures,
market sentiment, and technicals from the [Unusual Whales](https://unusualwhales.com)
REST API, scores them for **confluence**, and renders a dense terminal dashboard.

**This repo is read-only. It never places, modifies, or cancels an order.**
Execution stays in the brokerage with explicit per-order human confirmation.

---

## Why REST instead of MCP

The Unusual Whales MCP server exists and works well in Claude Code / Cursor / Windsurf.
This project uses the plain REST API instead, for three reasons:

1. **No connector dependency.** Claude.ai's custom-connector header auth is in beta
   rollout; the REST path works today regardless.
2. **Multi-endpoint joins.** Confluence scoring needs several datasets combined in one
   pass. That's a loop in Python, versus many sequential tool calls.
3. **Reproducibility.** Every scan writes a timestamped JSON snapshot next to the HTML,
   so any dashboard can be regenerated or audited later.

---

## Setup

```bash
git clone https://github.com/jeffczischke/Agentic-Terminal.git
cd Agentic-Terminal

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# paste your key from unusualwhales.com/settings/api-dashboard
```

`.env` is gitignored. **Never commit an API key.** If one is ever exposed, regenerate it —
refreshing deactivates the previous token.

---

## Usage

### Diagnose first

```bash
python -m agentic doctor
```

Answers the only question that matters when setup misbehaves: is it the **network**,
the **token**, or the **plan**? It makes one cheap authenticated call and interprets the
result:

| Result | Meaning |
|---|---|
| `PASS` | Token valid, REST path live. Ignore any MCP connector trouble — this path doesn't use it. |
| `401` | Token rejected. Regenerate it, and confirm your plan includes API access (UW sells API separately from the web subscription). |
| `403` + "allowlist" | A **network proxy** is blocking the host, not UW. Allow `api.unusualwhales.com` in egress settings. |
| `403` otherwise | Token valid but lacks scope for that endpoint. |
| `404` | Wrong path. Only endpoints in `uw_client.py` are real. |
| `0` | DNS/TLS/network failure reaching the host at all. |

### Run a scan

```bash
python -m agentic scan
python -m agentic scan --focus NVDA AVGO AMD MRVL --open
```

Writes `output/terminal-<timestamp>.html` and `output/snapshot-<timestamp>.json`.

### Inspect one dataset

```bash
python -m agentic raw congress --limit 40
python -m agentic raw darkpool
python -m agentic raw flow
```

---

## Confluence scoring

The core idea: **weight signals by how stale they are**, and **rank by breadth of
agreement rather than raw magnitude**.

| Source | Latency | Weight | Tier |
|---|---|---|---|
| Options flow | same day | 3.0 | Actionable |
| Dark pool | same day | 2.5 | Actionable |
| Insider (Form 4) | T+2 | 2.0 | Actionable |
| Institutional (13F) | T+45d | 1.0 | Context |
| Congress (STOCK Act) | T+45d | 0.5 | Context |

A congressional filing can describe a trade made six weeks ago, so it cannot confirm a
fresh catalyst — it's idea generation, never an entry trigger. Entry timing stays on
price, volume, and the 200-DMA.

Ranking sorts by **number of independent agreeing sources first**, magnitude second. A
ticker showing bullish flow *and* dark pool accumulation *and* insider buying is stronger
evidence than one dataset shouting alone.

Two deliberate asymmetries:

- **Insider selling is discounted to 0.4x** relative to buying. Executives sell for
  liquidity, diversification, and scheduled 10b5-1 plans; they buy for one reason.
- **Dark pool prints amplify rather than pick a side.** A block print marks institutional
  interest but is direction-agnostic without more context.

---

## Architecture

```
agentic/
  uw_client.py   REST wrapper: auth, retry, throttle, endpoint whitelist
  signals.py     fetch + normalise + confluence scoring
  dashboard.py   HTML terminal renderer
  config.py      env loading, watchlist, framework thresholds
  cli.py         doctor / scan / raw
output/          generated dashboards + JSON snapshots (gitignored)
```

### Endpoint whitelist

UW documents a set of commonly hallucinated endpoints that don't exist. `uw_client.py`
blocks them at call time so a bad path fails loudly instead of returning a confusing 404:

```python
BLACKLIST = ("/api/options/flow", "/api/flow", "/api/unusual-activity", "/api/v1/", ...)
```

Real paths live in the client's methods. If it isn't a method there, it isn't an endpoint.

### Degradation

One dead endpoint degrades one panel, never the whole scan. Failures are caught, the
specific diagnosis is surfaced in a banner, and **empty panels stay empty** — no
placeholder data is invented to make the dashboard look complete.

---

## Roadmap

- [ ] Merge live Robinhood positions (via MCP) into the dashboard's equity panel
- [ ] Candlestick rendering from UW OHLC endpoints
- [ ] 13F / institutional panel via the UW institutional dataset
- [ ] Historical snapshot diffing — what changed since the last scan
- [ ] Backtest confluence scores against forward returns to calibrate the weights

---

## Disclaimer

Not financial advice. Educational and research tooling only. All trading decisions and
their outcomes are the account holder's sole responsibility. Signals derived from public
disclosures lag reality and should never be treated as entry triggers on their own.

MIT
