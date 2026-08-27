"""Configuration. Secrets come from the environment, never from source."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"

load_dotenv(ROOT / ".env")


def get_api_key() -> str:
    key = os.getenv("UW_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "UW_API_KEY is not set.\n"
            "  1. cp .env.example .env\n"
            "  2. paste your key from unusualwhales.com/settings/api-dashboard\n"
            "Never commit .env — it is gitignored."
        )
    return key


RATE_LIMIT = int(os.getenv("UW_RATE_LIMIT_PER_MINUTE", "120"))
MAX_RETRIES = int(os.getenv("UW_MAX_RETRIES", "3"))

# Account context (read-only here; trading stays in Robinhood MCP with
# human confirmation — this repo never places orders).
ACCOUNT_NICKNAME = "Agentic"
ACCOUNT_NUMBER = os.getenv("RH_ACCOUNT_NUMBER", "566787347")

# The 46-symbol AI Trader watchlist.
WATCHLIST = [
    "APP", "IREN", "HOOD", "CEG", "MRVL", "LMT", "RTX", "AXON", "ANET", "AVGO",
    "RXRX", "NBIS", "BRK.B", "VLO", "OXY", "ORCL", "GEV", "DAL", "COST", "WMT",
    "AMZN", "UNH", "LLY", "BAC", "WFC", "JPM", "SQQQ", "TQQQ", "SOXS", "SOXL",
    "CRWV", "SPCX", "QQQ", "SPY", "RIVN", "PLTR", "SOFI", "GME", "AMC", "AAPL",
    "META", "TSLA", "AMD", "NVDA", "RKLB",
]

# Names to pull deep institutional detail on each scan. Keeping this short
# preserves the request budget; deep pulls are for positions plus candidates.
FOCUS_DEFAULT = ["NVDA", "AVGO", "AMD", "MRVL", "PLTR", "WFC"]

# Framework thresholds — mirrors the Master Instructions.
HARD_STOP_PCT = -0.15
SOFT_STOP_PCT = -0.08
VOLUME_GATE = 2.0          # x 30-day average
RR_STANDARD = 3.0
RR_LEVERAGED = 4.0
RR_MAX_SIZE = 5.0
MAX_POSITION_PCT = 0.20
MAX_POSITIONS = 5

# Signal latency tiers, in days. Drives the dashboard's trust ranking.
SIGNAL_LATENCY = {
    "flow": 0,
    "darkpool": 0,
    "market_tide": 0,
    "news": 0,
    "ark": 1,
    "insider": 2,
    "institutional": 45,
    "congress": 45,
}
