"""Command line entrypoint.

    python -m agentic doctor          diagnose connectivity and auth
    python -m agentic scan            full multi-source scan -> HTML dashboard
    python -m agentic scan --focus NVDA AVGO AMD
    python -m agentic raw congress    dump one dataset as JSON
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import webbrowser

from . import config, dashboard
from .signals import collect
from .uw_client import UWClient, UWConfig, UWError

BANNER = "AGENTIC//TERMINAL"


def _client() -> UWClient:
    return UWClient(
        UWConfig(
            api_key=config.get_api_key(),
            max_retries=config.MAX_RETRIES,
            rate_limit_per_minute=config.RATE_LIMIT,
        )
    )


def cmd_doctor(_: argparse.Namespace) -> int:
    """Answer the only question that matters when setup misbehaves:
    is it the network, the token, or the plan?"""
    print(f"{BANNER} :: diagnostics\n")

    try:
        key = config.get_api_key()
    except SystemExit as exc:
        print(exc)
        return 1
    print(f"  key loaded       {key[:8]}…{key[-4:]}  ({len(key)} chars)")

    with _client() as client:
        print("  endpoint         https://api.unusualwhales.com/api/market/market-tide")
        ok, message = client.healthcheck()
        print(f"  result           {'PASS' if ok else 'FAIL'}")
        print(f"  detail           {message}\n")

        if ok:
            print("  Token works over plain REST. The dashboard will run.")
            print("  If the Claude MCP connector still fails, the problem is the")
            print("  connector config, not your key or plan — and you can ignore it,")
            print("  because this path does not use MCP at all.")
            return 0

        print("  Next steps by failure type:")
        print("   401  regenerate the key; confirm your plan includes API access")
        print("        (UW sells API access separately from the web subscription)")
        print("   403  if it mentions an allowlist, a network proxy is blocking the")
        print("        host — allow api.unusualwhales.com in egress settings")
        print("   404  a path is wrong; only endpoints in uw_client.py are real")
        print("   0    DNS/TLS/network failure reaching the host at all")
        return 2


def cmd_scan(args: argparse.Namespace) -> int:
    focus = [s.upper() for s in (args.focus or config.FOCUS_DEFAULT)]
    print(f"{BANNER} :: scan  focus={', '.join(focus)}")

    with _client() as client:
        ok, message = client.healthcheck()
        if not ok:
            print(f"  preflight FAILED: {message}")
            print("  run `python -m agentic doctor` for a full diagnosis.")
            return 2

        print("  pulling signal layers…")
        data = collect(client, focus)

    ranked = data.get("confluence", [])
    print(f"  confluence rows  {len(ranked)}")
    for row in ranked[:5]:
        print(
            f"    {row['ticker']:<6} net {row['net']:+7.2f}  "
            f"{row['source_count']} src  {row['bias']}  ({', '.join(row['sources'])})"
        )

    path = dashboard.write(data)
    print(f"\n  dashboard        {path}")
    if args.open:
        webbrowser.open(path.as_uri())
    return 0


def cmd_raw(args: argparse.Namespace) -> int:
    with _client() as client:
        fetchers = {
            "congress": lambda: client.congress_trades(limit=args.limit),
            "insider": lambda: client.insider_transactions(limit=args.limit),
            "darkpool": lambda: client.darkpool_recent(limit=args.limit),
            "flow": lambda: client.flow_alerts(limit=args.limit),
            "tide": client.market_tide,
            "news": lambda: client.news_headlines(limit=args.limit),
        }
        if args.dataset not in fetchers:
            print(f"unknown dataset. choose from: {', '.join(fetchers)}")
            return 1
        try:
            print(json.dumps(fetchers[args.dataset](), indent=2, default=str))
        except UWError as exc:
            print(f"FAILED: {exc.diagnosis}")
            return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="  ! %(message)s")
    parser = argparse.ArgumentParser(prog="agentic", description=BANNER)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="diagnose connectivity, auth, and plan scope")

    p_scan = sub.add_parser("scan", help="run a full multi-source scan")
    p_scan.add_argument("--focus", nargs="*", help="tickers for deep pulls")
    p_scan.add_argument("--open", action="store_true", help="open the dashboard when done")

    p_raw = sub.add_parser("raw", help="dump one dataset as JSON")
    p_raw.add_argument("dataset", help="congress|insider|darkpool|flow|tide|news")
    p_raw.add_argument("--limit", type=int, default=25)

    args = parser.parse_args(argv)
    handlers = {"doctor": cmd_doctor, "scan": cmd_scan, "raw": cmd_raw}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
