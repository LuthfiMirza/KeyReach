"""
channels/twitter.py — Twitter / X.com channel
==============================================
Attempts to fetch public Twitter/X profile pages or tweet threads.

Strategy (in order):
    1. Use Nitter public instance (privacy-respecting Twitter frontend)
       — no API key required, works for most public profiles.
    2. Falls back to direct twitter.com (often blocked by JS requirements,
       so will trigger the router's Jina fallback automatically).

Notes
-----
* We deliberately do NOT use the paid Twitter API to keep this tool
  free and accessible. For production use, swap in a proper API key.
* Rate-limit gracefully: if Nitter returns 429, raise so the router
  falls back to Jina.
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from channels.base import BaseChannel
from core.logger import get_logger
from core.ssl_compat import get_ssl_verify

logger = get_logger(__name__)

# Known public Nitter instances (ordered by reliability)
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; KeyReach-Agent/1.0)"
    ),
}


class TwitterChannel(BaseChannel):
    """
    Fetches Twitter/X profiles and tweets via public Nitter instances.
    """

    def fetch(self, url: str, timeout: int = 15) -> str:
        """
        Convert a twitter.com/x.com URL to a Nitter URL and fetch it.

        Raises RuntimeError if all Nitter instances are unavailable.
        """
        path = _extract_path(url)
        errors: list[str] = []

        for instance in NITTER_INSTANCES:
            nitter_url = f"{instance}{path}"
            logger.debug("TwitterChannel trying: %s", nitter_url)
            try:
                resp = requests.get(nitter_url, headers=HEADERS, timeout=timeout, verify=get_ssl_verify())
                if resp.status_code == 429:
                    errors.append(f"{instance}: rate limited (429)")
                    continue
                resp.raise_for_status()
                return _parse_nitter(resp.text, nitter_url)
            except requests.RequestException as exc:
                errors.append(f"{instance}: {exc}")
                logger.warning("Nitter instance %s failed: %s", instance, exc)

        raise RuntimeError(
            f"All Nitter instances failed for '{url}'. Errors: {'; '.join(errors)}"
        )

    def ping(self) -> tuple[bool, str]:
        """Ping first available Nitter instance."""
        for instance in NITTER_INSTANCES:
            try:
                resp = requests.get(instance, headers=HEADERS, timeout=5, verify=get_ssl_verify())
                if resp.ok:
                    return True, f"Nitter OK ({instance})"
            except Exception:  # noqa: BLE001
                pass
        return False, "All Nitter instances unreachable"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_path(url: str) -> str:
    """
    Strip the domain from a twitter.com / x.com URL and return the path.

    Examples
    --------
    https://twitter.com/elonmusk → /elonmusk
    https://x.com/elonmusk/status/123 → /elonmusk/status/123
    """
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.path or "/"


def _parse_nitter(html: str, source_url: str) -> str:
    """Extract tweet / profile text from Nitter HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Try to grab tweets
    tweets = soup.select(".tweet-content")
    if tweets:
        lines = [f"## Twitter content via Nitter ({source_url})\n"]
        for i, t in enumerate(tweets[:20], 1):
            lines.append(f"**Tweet {i}:** {t.get_text(strip=True)}\n")
        return "\n".join(lines)

    # Fallback: full page text
    body = soup.find("body")
    return body.get_text(separator="\n", strip=True) if body else html[:2000]
