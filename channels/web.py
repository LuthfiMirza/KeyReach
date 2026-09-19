"""
channels/web.py — Generic HTTP channel (Primary backend A)
===========================================================
Uses requests + BeautifulSoup to fetch and clean any public web page.

Security features (via SecureFetcher):
    * Blocks private/localhost IP ranges (SSRF protection)
    * Validates URL scheme (http/https only)
    * Strips scripts, styles, and tracking pixels from HTML
    * Enforces Content-Length / response size cap
"""

from __future__ import annotations

import re
import socket
import ipaddress
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from channels.base import BaseChannel
from core.logger import get_logger
from core.ssl_compat import get_ssl_verify

logger = get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB cap
ALLOWED_SCHEMES = {"http", "https"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; KeyReach-Agent/1.0; "
        "+https://github.com/your-org/keyreach)"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Tags to remove wholesale before text extraction
NOISE_TAGS = [
    "script", "style", "noscript", "iframe", "svg", "img",
    "video", "audio", "canvas", "figure", "aside", "nav",
    "footer", "header", "form", "button",
]


class WebChannel(BaseChannel):
    """
    Fetches public web pages using direct HTTP GET.
    Acts as Backend A in the fallback chain.
    """

    def fetch(self, url: str, timeout: int = 15) -> str:
        """
        Fetch *url* and return its main text content as clean plain text.

        Raises
        ------
        ValueError   on blocked or invalid URLs
        RuntimeError on HTTP errors or oversized responses
        """
        _validate_url(url)

        logger.debug("WebChannel.fetch → %s (timeout=%s)", url, timeout)
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
            verify=get_ssl_verify(),
        )
        resp.raise_for_status()

        # Stream-read with size cap
        chunks: list[bytes] = []
        read = 0
        for chunk in resp.iter_content(chunk_size=8192):
            read += len(chunk)
            if read > MAX_RESPONSE_BYTES:
                raise RuntimeError(
                    f"Response exceeds size limit ({MAX_RESPONSE_BYTES // 1024}KB). "
                    "Use --channel jina for large pages."
                )
            chunks.append(chunk)

        raw_html = b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")
        return _html_to_text(raw_html, url)

    def ping(self) -> tuple[bool, str]:
        """Check that we can reach the public internet."""
        try:
            resp = requests.get(
                "https://httpbin.org/get", headers=HEADERS, timeout=5, verify=get_ssl_verify()
            )
            if resp.status_code == 200:
                return True, "ok"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_url(url: str) -> None:
    """SSRF guard: reject private IPs, localhost, and bad schemes."""
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Blocked scheme: '{parsed.scheme}'. Only http/https allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname.")

    # Reject obvious localhost aliases
    if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise ValueError(f"SSRF blocked: hostname '{hostname}' is localhost.")

    # Resolve and check IP range
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(hostname))
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError(f"SSRF blocked: IP '{ip}' is in a private/reserved range.")
    except (socket.gaierror, ValueError):
        # DNS failure or already-raised ValueError — propagate
        raise


def _html_to_text(html: str, url: str) -> str:
    """Parse HTML and extract readable text, removing noise tags."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise
    for tag in soup(NOISE_TAGS):
        tag.decompose()

    # Try to isolate main content
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id=re.compile(r"(content|main|body)", re.I))
        or soup.find("body")
        or soup
    )

    # Extract and clean text
    text = main.get_text(separator="\n", strip=True)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
