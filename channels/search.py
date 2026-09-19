"""
channels/search.py — Web search channel
========================================
Performs a web search using DuckDuckGo's HTML interface (no API key required).

Returns a list of structured result dicts, suitable for AI Agent consumption.

For production, swap in Google Custom Search API or Brave Search API
by subclassing BaseChannel and updating router.py.
"""

from __future__ import annotations

import ssl
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup

from channels.base import BaseChannel
from core.logger import get_logger

logger = get_logger(__name__)

DDG_URL = "https://html.duckduckgo.com/html/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# macOS Python 3.9 SSL fix — use certifi bundle
try:
    import certifi
    _SSL_VERIFY: str | bool = certifi.where()
except ImportError:
    _SSL_VERIFY = True


class SearchChannel(BaseChannel):
    """
    Searches the web via DuckDuckGo HTML endpoint.
    No API key or account required.
    """

    def fetch(self, url: str, timeout: int = 15) -> str:
        """Not used directly; call search() instead."""
        raise NotImplementedError("SearchChannel.fetch is not supported. Use search().")

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """
        Search DuckDuckGo for *query* and return up to *limit* results.

        Returns
        -------
        list of {title, url, snippet}
        """
        logger.debug("SearchChannel.search → '%s' (limit=%s)", query, limit)

        resp = requests.post(
            DDG_URL,
            data={"q": query, "kl": "us-en"},
            headers=HEADERS,
            timeout=15,
            allow_redirects=True,
            verify=_SSL_VERIFY,
        )
        resp.raise_for_status()
        return _parse_results(resp.text, limit)

    def ping(self) -> tuple[bool, str]:
        try:
            resp = requests.get(DDG_URL, headers=HEADERS, timeout=5, verify=_SSL_VERIFY)
            if resp.ok:
                return True, "DuckDuckGo HTML reachable"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_results(html: str, limit: int) -> list[dict]:
    """Parse DuckDuckGo HTML search results page."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []

    for result in soup.select(".result"):
        if len(results) >= limit:
            break

        title_el = result.select_one(".result__title a")
        snippet_el = result.select_one(".result__snippet")

        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        # DuckDuckGo wraps URLs — extract the real one
        real_url = _extract_real_url(href)

        if real_url:
            results.append({
                "title": title,
                "url": real_url,
                "snippet": snippet,
            })

    return results


def _extract_real_url(href: str) -> str | None:
    """
    DDG wraps outbound links.  Extract the real destination from the
    'uddg' query parameter, falling back to the raw href.
    """
    if not href:
        return None
    parsed = urllib.parse.urlparse(href)
    params = urllib.parse.parse_qs(parsed.query)
    if "uddg" in params:
        return urllib.parse.unquote(params["uddg"][0])
    if href.startswith("http"):
        return href
    return None
