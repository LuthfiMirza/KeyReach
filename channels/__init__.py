"""
channels — Pluggable backend modules for KeyReach.

Each channel must implement:
    fetch(url: str, timeout: int) -> str
    ping() -> tuple[bool, str]
"""
