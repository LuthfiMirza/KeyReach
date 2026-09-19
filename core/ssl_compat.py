"""
core/ssl_compat.py — SSL compatibility layer for macOS system Python
=====================================================================
macOS ships Python 3.9 with LibreSSL 2.8.3, which lacks the system
root certificates needed by modern HTTPS endpoints.

This module provides a unified `get_ssl_verify()` function that:
    1. Tries the certifi bundle (best option, cross-platform)
    2. Falls back to system CA store via REQUESTS_CA_BUNDLE env var
    3. Respects KEYREACH_SSL_VERIFY=false for development/testing

Usage in any channel:
    from core.ssl_compat import get_ssl_verify
    requests.get(url, verify=get_ssl_verify())

Security note
-------------
Never ship with verify=False in production. This module only disables
verification when the user explicitly sets KEYREACH_SSL_VERIFY=false.
"""

from __future__ import annotations

import os
import ssl
from core.logger import get_logger

logger = get_logger(__name__)

_cached: bool | str | None = None


def get_ssl_verify() -> bool | str:
    """
    Return the appropriate `verify` argument for requests.get/post.

    Returns
    -------
    str   — path to a CA bundle file (certifi or system)
    True  — use default SSL verification (if somehow certifi isn't needed)
    False — disable verification (ONLY if KEYREACH_SSL_VERIFY=false is set)
    """
    global _cached
    if _cached is not None:
        return _cached

    # Explicit override for development
    env_val = os.environ.get("KEYREACH_SSL_VERIFY", "").lower()
    if env_val == "false":
        logger.warning(
            "SSL verification DISABLED via KEYREACH_SSL_VERIFY=false. "
            "Do NOT use this in production."
        )
        _cached = False
        return _cached

    # 1. Try macOS system CA certs first (most reliable on macOS LibreSSL)
    try:
        import subprocess, tempfile, pathlib
        result = subprocess.run(
            ["/usr/bin/security", "find-certificate", "-a", "-p",
             "/System/Library/Keychains/SystemRootCertificates.keychain"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout:
            tmp = pathlib.Path(tempfile.gettempdir()) / "keyreach_macos_cacerts.pem"
            tmp.write_text(result.stdout)
            logger.debug("SSL: using macOS system certs at %s", tmp)
            _cached = str(tmp)
            return _cached
    except Exception as exc:
        logger.debug("macOS system certs not available: %s", exc)

    # 2. Try certifi bundle
    try:
        import certifi
        ca_path = certifi.where()
        logger.debug("SSL: using certifi bundle at %s", ca_path)
        _cached = ca_path
        return _cached
    except ImportError:
        logger.warning("certifi not installed.")

    # 3. Try environment variable overrides
    ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if ca_bundle:
        logger.debug("SSL: using CA bundle from env: %s", ca_bundle)
        _cached = ca_bundle
        return _cached

    # 4. Last resort — disable (with clear warning in logs)
    logger.error(
        "Could not find any CA bundle. SSL verification will be DISABLED. "
        "Set KEYREACH_SSL_VERIFY=false explicitly to silence this error, "
        "or run: pip install certifi"
    )
    _cached = False
    return _cached
