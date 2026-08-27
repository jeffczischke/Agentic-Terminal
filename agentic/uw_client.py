"""
Unusual Whales REST client.

Endpoint paths are taken verbatim from the official UW skill reference
(https://unusualwhales.com/skill.md). UW documents a set of commonly
hallucinated endpoints that do not exist; those are blocked here so a typo
fails loudly at call time instead of returning a confusing 404 payload.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Iterable

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://api.unusualwhales.com"
CLIENT_API_ID = "100001"

# Paths UW explicitly documents as non-existent but frequently invented.
BLACKLIST = (
    "/api/options/flow",
    "/api/flow",
    "/api/flow/live",
    "/api/unusual-activity",
    "/api/v1/",
    "/api/v2/",
)


class UWError(RuntimeError):
    """Raised for non-retryable API failures, with diagnosis attached."""

    def __init__(self, status: int, path: str, body: str):
        self.status = status
        self.path = path
        self.body = body
        super().__init__(f"{status} on {path}: {body[:300]}")

    @property
    def diagnosis(self) -> str:
        if self.status == 401:
            return (
                "401 Unauthorized — the token was rejected. Check the key is "
                "current (regenerating deactivates the previous one) and that "
                "your plan includes API access."
            )
        if self.status == 403:
            if "allowlist" in self.body.lower():
                return (
                    "403 from a network egress proxy, not from UW. The host "
                    "is blocked before the request leaves this machine."
                )
            return "403 Forbidden — the token is valid but lacks scope for this endpoint."
        if self.status == 404:
            return (
                "404 Route not found — the path is wrong. Only paths in "
                "ENDPOINTS below are real; check for a typo or a made-up route."
            )
        if self.status == 429:
            return "429 Rate limited — slow down or raise the plan's per-minute cap."
        return f"HTTP {self.status}."


@dataclass
class UWConfig:
    api_key: str
    timeout: float = 20.0
    max_retries: int = 3
    rate_limit_per_minute: int = 120


class UWClient:
    def __init__(self, config: UWConfig):
        if not config.api_key:
            raise ValueError("Missing UW API key. Set UW_API_KEY in your .env file.")
        self.cfg = config
        self._min_interval = 60.0 / max(1, config.rate_limit_per_minute)
        self._last_call = 0.0
        self._client = requests.Session()
        self._client.headers.update(
            {
                "Authorization": f"Bearer {config.api_key}",
                "Accept": "application/json",
                "UW-CLIENT-API-ID": CLIENT_API_ID,
            }
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "UWClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.monotonic()

    def get(self, path: str, params: dict | None = None) -> Any:
        """GET a whitelisted path. All UW endpoints are GET-only."""
        for bad in BLACKLIST:
            if path.startswith(bad):
                raise ValueError(
                    f"{path} is on the UW hallucination blacklist and does not exist."
                )

        attempt = 0
        while True:
            self._throttle()
            try:
                resp = self._client.get(
                    f"{BASE_URL}{path}", params=params, timeout=self.cfg.timeout
                )
            except requests.RequestException as exc:
                attempt += 1
                if attempt > self.cfg.max_retries:
                    raise UWError(0, path, f"network error: {exc}") from exc
                time.sleep(2**attempt)
                continue

            if resp.status_code == 200:
                payload = resp.json()
                # UW wraps most collections in {"data": [...]}
                return payload.get("data", payload) if isinstance(payload, dict) else payload

            if resp.status_code in (429, 500, 502, 503, 504):
                attempt += 1
                if attempt > self.cfg.max_retries:
                    raise UWError(resp.status_code, path, resp.text)
                time.sleep(2**attempt)
                continue

            raise UWError(resp.status_code, path, resp.text)

    # ---------- Smart money ----------

    def congress_trades(self, limit: int = 100, ticker: str | None = None) -> Any:
        params: dict[str, Any] = {"limit": limit}
        if ticker:
            params["ticker"] = ticker
        return self.get("/api/congress/recent-trades", params)

    def insider_transactions(self, limit: int = 100, ticker: str | None = None) -> Any:
        params: dict[str, Any] = {"limit": limit}
        if ticker:
            params["ticker"] = ticker
        return self.get("/api/insider/transactions", params)

    # ---------- Institutional footprint ----------

    def darkpool_ticker(self, ticker: str, limit: int = 50) -> Any:
        return self.get(f"/api/darkpool/{ticker.upper()}", {"limit": limit})

    def darkpool_recent(self, limit: int = 100) -> Any:
        return self.get("/api/darkpool/recent", {"limit": limit})

    # ---------- Options positioning ----------

    def flow_alerts(
        self,
        ticker: str | None = None,
        min_premium: int = 50_000,
        limit: int = 50,
        is_otm: bool | None = None,
    ) -> Any:
        params: dict[str, Any] = {"limit": limit, "min_premium": min_premium}
        if ticker:
            params["ticker_symbol"] = ticker.upper()
        if is_otm is not None:
            params["is_otm"] = is_otm
        return self.get("/api/option-trades/flow-alerts", params)

    def spot_gex_by_strike(self, ticker: str) -> Any:
        return self.get(f"/api/stock/{ticker.upper()}/spot-exposures/strike")

    def options_volume(self, ticker: str) -> Any:
        return self.get(f"/api/stock/{ticker.upper()}/options-volume")

    def net_premium_ticks(self, ticker: str) -> Any:
        return self.get(f"/api/stock/{ticker.upper()}/net-prem-ticks")

    # ---------- Market context ----------

    def market_tide(self, interval_5m: bool = False) -> Any:
        return self.get("/api/market/market-tide", {"interval_5m": interval_5m})

    def news_headlines(self, limit: int = 40) -> Any:
        return self.get("/api/news/headlines", {"limit": limit})

    # ---------- Technicals ----------

    def technical_indicator(
        self,
        ticker: str,
        function: str,
        interval: str = "daily",
        time_period: int = 200,
        series_type: str = "close",
    ) -> Any:
        """function: SMA, EMA, RSI, MACD, BBANDS, STOCH, ADX, ATR, OBV, VWAP, CCI, WILLR, AROON, MFI"""
        return self.get(
            f"/api/stock/{ticker.upper()}/technical-indicator/{function.upper()}",
            {"interval": interval, "time_period": time_period, "series_type": series_type},
        )

    # ---------- Diagnostics ----------

    def healthcheck(self) -> tuple[bool, str]:
        """Cheapest possible authenticated call. Returns (ok, message)."""
        try:
            self.get("/api/market/market-tide", {"interval_5m": False})
            return True, "200 OK — token valid, MCP-free REST path is live."
        except UWError as exc:
            return False, exc.diagnosis
        except Exception as exc:  # noqa: BLE001
            return False, f"Unexpected failure: {exc}"


def batch(items: Iterable[str], size: int) -> Iterable[list[str]]:
    chunk: list[str] = []
    for item in items:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
