"""
router.py — AgentRouter
=======================
Central routing brain of KeyReach.  Selects the best backend channel for a
given URL / query, executes it, and falls back gracefully when it fails.

Design principles
-----------------
* **Never crash/panic** — every exception is caught and returned as a
  structured error dict that an AI Agent can parse.
* **Priority ordering** — backends are tried in priority order; the first
  that succeeds wins.
* **Pluggable** — adding a new backend only requires dropping a module in
  `channels/` and registering it here.
"""

from __future__ import annotations

import re
import time
from typing import Any

from core.logger import get_logger
from channels.web import WebChannel
from channels.twitter import TwitterChannel
from channels.jina import JinaChannel       # Free fallback: Jina Reader API
from channels.search import SearchChannel
from channels.secure_fetcher import SecureFetcherChannel

logger = get_logger(__name__)


# ── Type alias ────────────────────────────────────────────────────────────────
Result = dict[str, Any]


# ── Auto-Routing Logic (Deteksi Otomatis) ──────────────────────────────────────
# Maps regex patterns against the incoming URL to choose the right channel automatically.
# Jika argumen url mengandung twitter.com atau x.com, sistem akan otomatis
# menggunakan channel twitter tanpa pengguna mengetik --channel twitter.
DOMAIN_ROUTING_TABLE: list[tuple[str, str]] = [
    (r"(twitter\.com|x\.com)", "twitter"),
    (r"(reddit\.com)", "web"),
    (r"(youtube\.com|youtu\.be)", "web"),
    (r".*", "web"),  # catch-all
]


class AgentRouter:
    """
    Multi-backend router with automatic fallback.

    Fetch priority (per channel):
        1. Primary channel for the URL (e.g. TwitterChannel for twitter.com)
        2. Generic WebChannel  (direct HTTP GET + BeautifulSoup)
        3. JinaChannel         (free Jina Reader API — no key required)

    If all three fail, returns a structured error JSON — never raises.
    """

    def __init__(self) -> None:
        # Instantiate all available channels once; they are reused across calls.
        self._channels: dict[str, Any] = {
            "twitter": TwitterChannel(),
            "web": WebChannel(),
            "jina": JinaChannel(),
            "search": SearchChannel(),
            "secure": SecureFetcherChannel(),
        }
        logger.info("AgentRouter initialised with channels: %s", list(self._channels.keys()))

    # ── Public API ─────────────────────────────────────────────────────────────

    def fetch(
        self,
        url: str,
        timeout: int = 15,
        preferred_channel: str | None = None,
    ) -> Result:
        """
        Fetch content from *url* using the best available backend.

        Parameters
        ----------
        url:               Target URL.
        timeout:           Per-backend timeout in seconds.
        preferred_channel: Override auto-detection (e.g. "twitter", "web").

        Returns
        -------
        dict with keys:
            status          – "ok" | "error"
            url             – original URL
            content         – fetched text/Markdown (on success)
            backend_used    – name of the backend that succeeded
            backends_attempted – ordered list of tried backends
            error           – human-readable message (on failure)
            elapsed_ms      – total time spent across all attempts
        """
        t0 = time.perf_counter()
        backends_attempted: list[str] = []

        # Build the ordered list of backends to try
        pipeline = self._build_pipeline(url, preferred_channel)
        logger.info("fetch pipeline for %s: %s", url, pipeline)

        for backend_name in pipeline:
            channel = self._channels.get(backend_name)
            if channel is None:
                logger.warning("Unknown channel '%s', skipping.", backend_name)
                continue

            backends_attempted.append(backend_name)
            logger.info("Trying backend '%s' for %s …", backend_name, url)

            try:
                content = channel.fetch(url=url, timeout=timeout)
                elapsed = int((time.perf_counter() - t0) * 1000)
                logger.info("Backend '%s' succeeded in %dms.", backend_name, elapsed)
                return {
                    "status": "ok",
                    "url": url,
                    "content": content,
                    "backend_used": backend_name,
                    "backends_attempted": backends_attempted,
                    "elapsed_ms": elapsed,
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("Backend '%s' failed: %s", backend_name, exc)
                # Continue to next backend

        # All backends exhausted
        elapsed = int((time.perf_counter() - t0) * 1000)
        logger.error("All backends failed for %s after %dms.", url, elapsed)
        return {
            "status": "error",
            "url": url,
            "error": "All backends failed. The target may be unavailable or protected.",
            "backends_attempted": backends_attempted,
            "elapsed_ms": elapsed,
            "hint": (
                "Try again later, or check if the URL is publicly accessible. "
                "For paywalled / JS-heavy pages, no backend can currently bypass them."
            ),
        }

    def search(self, query: str, limit: int = 5) -> Result:
        """
        Web search using the SearchChannel (DuckDuckGo HTML scrape by default).

        Returns
        -------
        dict with keys:
            status   – "ok" | "error"
            query    – original query string
            results  – list of {title, url, snippet} (on success)
            error    – message (on failure)
        """
        t0 = time.perf_counter()
        channel = self._channels["search"]
        try:
            results = channel.search(query=query, limit=limit)
            elapsed = int((time.perf_counter() - t0) * 1000)
            return {
                "status": "ok",
                "query": query,
                "results": results,
                "count": len(results),
                "elapsed_ms": elapsed,
            }
        except Exception as exc:  # noqa: BLE001
            elapsed = int((time.perf_counter() - t0) * 1000)
            logger.error("Search failed: %s", exc)
            return {
                "status": "error",
                "query": query,
                "error": str(exc),
                "elapsed_ms": elapsed,
            }

    def health_check(self) -> Result:
        """
        Ping each registered channel and report availability.

        Returns
        -------
        dict with keys:
            status   – "ok" if at least one channel is healthy
            channels – list of {name, healthy, detail}
        """
        reports = []
        for name, channel in self._channels.items():
            try:
                healthy, detail = channel.ping()
            except Exception as exc:  # noqa: BLE001
                healthy, detail = False, str(exc)
            reports.append({"name": name, "healthy": healthy, "detail": detail})
            logger.info("Health check '%s': healthy=%s detail=%s", name, healthy, detail)

        overall = any(r["healthy"] for r in reports)
        return {
            "status": "ok" if overall else "error",
            "channels": reports,
            "summary": f"{sum(r['healthy'] for r in reports)}/{len(reports)} channels healthy",
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _build_pipeline(
        self,
        url: str,
        preferred_channel: str | None,
    ) -> list[str]:
        """
        Return an ordered list of backend names to try for *url*.

        Strategy:
            1. If *preferred_channel* is explicitly given, put it first.
            2. Auto-detect the primary channel from DOMAIN_ROUTING_TABLE.
            3. Append universal fallbacks: generic web, then Jina.
        """
        pipeline: list[str] = []

        if preferred_channel and preferred_channel in self._channels:
            pipeline.append(preferred_channel)

        # Auto-detect from routing table
        auto = self._detect_channel(url)
        if auto not in pipeline:
            pipeline.append(auto)

        # Fallbacks — always append generic web + Jina, deduped
        for fallback in ("web", "jina"):
            if fallback not in pipeline:
                pipeline.append(fallback)

        return pipeline

    @staticmethod
    def _detect_channel(url: str) -> str:
        """Match *url* against DOMAIN_ROUTING_TABLE and return channel name."""
        for pattern, channel in DOMAIN_ROUTING_TABLE:
            if re.search(pattern, url, re.IGNORECASE):
                return channel
        return "web"
