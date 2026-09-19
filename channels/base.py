"""
channels/base.py — Abstract base class for all KeyReach channels.

Every channel MUST inherit from BaseChannel and implement:
    fetch(url, timeout) -> str
    ping()              -> tuple[bool, str]
"""

from __future__ import annotations
from abc import ABC, abstractmethod


class BaseChannel(ABC):
    """Contract that all backend channels must satisfy."""

    @abstractmethod
    def fetch(self, url: str, timeout: int = 15) -> str:
        """
        Retrieve content from *url*.

        Returns the page content as plain text or Markdown.
        Raises any exception on failure — the router will catch it.
        """

    @abstractmethod
    def ping(self) -> tuple[bool, str]:
        """
        Quick health check.

        Returns
        -------
        (True, "ok")             on success
        (False, "error message") on failure
        """
