"""
channels/jina.py — Jina Reader API channel (Universal Fallback — Backend B)
============================================================================
Jina Reader (r.jina.ai) converts any URL to clean Markdown for free,
with no API key required.

This is the *last-resort* fallback in the router's pipeline — it handles
pages that BeautifulSoup + requests cannot parse (JS-heavy SPAs, etc.).

Docs: https://jina.ai/reader
"""

from __future__ import annotations

import requests

from channels.base import BaseChannel
from core.logger import get_logger
from core.ssl_compat import get_ssl_verify

logger = get_logger(__name__)

JINA_BASE = "https://r.jina.ai/"

HEADERS = {
    "Accept": "text/plain, text/markdown",
    "User-Agent": "KeyReach-Agent/1.0 (+https://github.com/your-org/keyreach)",
    # Optional: add  "Authorization": "Bearer <YOUR_JINA_KEY>"  for higher rate limits
    "X-Return-Format": "markdown",      # Ask Jina for Markdown output
    "X-No-Cache": "true",               # Always fresh content
}


class JinaChannel(BaseChannel):
    """
    Fetches any URL via Jina Reader API and returns clean Markdown.

    Acts as Backend B (universal fallback) in the routing pipeline.
    No API key required for basic usage.
    """

    def fetch(self, url: str, timeout: int = 20) -> str:
        """
        Call Jina Reader API to convert *url* to Markdown.

        Parameters
        ----------
        url:     Target URL (passed directly to Jina).
        timeout: HTTP timeout in seconds (use slightly higher than other
                 channels because Jina itself fetches + renders the page).

        Returns
        -------
        str — Markdown content of the page.

        Raises
        ------
        RuntimeError on non-2xx responses.
        """
        jina_url = f"{JINA_BASE}{url}"
        logger.debug("JinaChannel.fetch → %s", jina_url)

        resp = requests.get(jina_url, headers=HEADERS, timeout=timeout, verify=get_ssl_verify())

        if resp.status_code == 429:
            raise RuntimeError(
                "Jina Reader rate-limited (429). "
                "Add a free API key via https://jina.ai to increase limits."
            )

        resp.raise_for_status()

        content = resp.text.strip()
        if not content:
            raise RuntimeError("Jina Reader returned empty content for this URL.")

        return content

    def ping(self) -> tuple[bool, str]:
        """Verify Jina Reader API is reachable."""
        try:
            # Use a lightweight, always-available URL for the ping
            test_url = f"{JINA_BASE}https://example.com"
            resp = requests.get(test_url, headers=HEADERS, timeout=10, verify=get_ssl_verify())
            if resp.ok and len(resp.text) > 50:
                return True, "Jina Reader API reachable"
            return False, f"Jina returned unexpected response (HTTP {resp.status_code})"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
