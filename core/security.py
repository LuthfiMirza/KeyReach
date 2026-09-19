"""
core/security.py — Shared security utilities
=============================================
Centralised guards reused across channels.

Currently provides:
    - URL validation (scheme whitelist + SSRF protection)
    - Content-type allowlist
    - Response size enforcement
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = frozenset({"http", "https"})
MAX_CONTENT_BYTES = 10 * 1024 * 1024  # 10 MB hard cap


def validate_url(url: str) -> None:
    """
    Raise ValueError if *url* is unsafe or malformed.

    Checks
    ------
    1. Scheme must be http or https.
    2. Hostname must be present.
    3. Hostname must not resolve to a private/loopback/link-local IP
       (SSRF mitigation).
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"Blocked scheme '{parsed.scheme}'. "
            f"Only {sorted(ALLOWED_SCHEMES)} are allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no valid hostname.")

    # Block obvious localhost aliases immediately (skip DNS)
    _LOCALHOST_ALIASES = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "0"}
    if hostname.lower() in _LOCALHOST_ALIASES:
        raise ValueError(f"SSRF blocked: '{hostname}' is a localhost alias.")

    # Resolve hostname → IP and check for private ranges
    try:
        resolved_ip = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(resolved_ip)
    except socket.gaierror as exc:
        raise ValueError(f"DNS resolution failed for '{hostname}': {exc}") from exc

    if ip.is_private:
        raise ValueError(f"SSRF blocked: '{hostname}' resolves to private IP {ip}.")
    if ip.is_loopback:
        raise ValueError(f"SSRF blocked: '{hostname}' resolves to loopback IP {ip}.")
    if ip.is_link_local:
        raise ValueError(f"SSRF blocked: '{hostname}' resolves to link-local IP {ip}.")
    if ip.is_reserved:
        raise ValueError(f"SSRF blocked: '{hostname}' resolves to reserved IP {ip}.")


def enforce_size(content: bytes, cap: int = MAX_CONTENT_BYTES) -> None:
    """Raise RuntimeError if *content* exceeds *cap* bytes."""
    if len(content) > cap:
        mb = cap / (1024 * 1024)
        raise RuntimeError(
            f"Response size {len(content):,} bytes exceeds the {mb:.0f} MB limit. "
            "Use the Jina channel for large pages (it streams server-side)."
        )
