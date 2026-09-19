"""
channels/secure_fetcher.py — Secure Web Scraper Channel
======================================================
This channel uses local browser cookies for authenticated scraping.
CRITICAL FOCUS: SECURITY AND DATA ISOLATION (Zero-Trust).

Security Architecture:
1. ISOLATED COOKIE EXTRACTION: Only extracts cookies for the requested domain using `browser-cookie3`.
2. RAM-ONLY: Cookies are strictly kept in memory within the httpx.Client session. No logging of cookies.
3. STRICT GET: Only HTTP GET is supported. Hardcoded block for POST/PUT/PATCH/DELETE.
4. SAFE PARSING: Never returns raw HTML to avoid leaking hidden tokens. Parses clean text into JSON.
5. SQLITE LOCK HANDLING: Gracefully handles locked browser databases.
"""

from __future__ import annotations

import sqlite3
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from channels.base import BaseChannel
from core.logger import get_logger

logger = get_logger(__name__)

# Modern User-Agent for anti-bot spoofing
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class SecureFetcherChannel(BaseChannel):
    """
    Secure authenticated fetcher using local browser cookies.
    """

    def fetch(self, url: str, timeout: int = 15) -> str:
        """
        Fetch data from the given URL securely.
        Returns JSON string representation of the parsed content.
        """
        import json
        data = self.get_data(url, timeout)
        # Return as JSON string since BaseChannel expects a string return
        # The router will pass this to the AI, which can parse it.
        return json.dumps(data, ensure_ascii=False)

    def ping(self) -> tuple[bool, str]:
        return True, "SecureFetcher available (requires local Chrome)"

    def _fetch_raw_html(self, url: str, timeout: int = 15) -> str:
        """
        Internal method to fetch raw HTML securely. 
        DO NOT return this to the terminal directly.
        """
        # 1. URL Validation (HTTPS only)
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https":
            return '{"error": "Hanya URL dengan skema https:// yang diizinkan untuk keamanan."}'
        
        domain = parsed_url.netloc

        # 2. Extract cookies securely (Isolated to domain)
        try:
            import browser_cookie3
            # Extract cookies ONLY for this specific domain
            # Example: if domain is 'twitter.com', we get '.twitter.com' cookies
            domain_param = f".{domain.replace('www.', '')}"
            logger.info("Extracting cookies for domain: %s", domain_param)
            
            # Memuat cookie dari Chrome secara aman
            cj = browser_cookie3.chrome(domain_name=domain_param)
            
        except sqlite3.OperationalError:
            return '{"error": "Browser Chrome sedang digunakan, tolong minta pengguna menutupnya sebentar atau gunakan backend lain."}'
        except ImportError:
            return '{"error": "Library browser-cookie3 tidak terinstall."}'
        except Exception as e:
            # We do NOT log the exception details to avoid leaking sensitive data
            logger.warning("Failed to extract cookies safely.")
            return '{"error": "Gagal mengekstrak cookie dari browser."}'

        # 3. HTTPX Client setup (RAM-Only)
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        try:
            # Strict GET - We don't expose any other methods
            with httpx.Client(cookies=cj, headers=headers, timeout=timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                html_content = response.text
                return html_content
                
        except httpx.RequestError as exc:
            logger.warning("HTTPX Request failed for %s", url)
            return f'{{"error": "Gagal melakukan request: {exc}"}}'
        except Exception as exc:
            logger.warning("HTTPX Unexpected error")
            return '{"error": "Terjadi kesalahan saat memuat halaman."}'

    def get_data(self, url: str, timeout: int = 15) -> dict:
        """
        Strict GET method to fetch and clean data.
        """
        html_content = self._fetch_raw_html(url, timeout)
        
        # If it's a JSON error string, return it as dict
        if html_content.startswith('{"error"'):
            import json
            try:
                return json.loads(html_content)
            except:
                pass

        # 4. Safe Parsing (No raw HTML)
        return self._parse_to_clean_json(html_content)

    def _parse_to_clean_json(self, html: str) -> dict:
        """
        Extract title, meta description, and article/paragraph texts.
        Masks all other potentially sensitive HTML content.
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract title
        title = soup.title.string if soup.title else "No Title"
        
        # Extract meta description
        meta_desc = ""
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag and desc_tag.get("content"):
            meta_desc = desc_tag["content"]
            
        # Extract text content safely
        # We target specific text containers to avoid hidden inputs/tokens
        content_texts = []
        
        # Try <article> first
        articles = soup.find_all("article")
        if articles:
            for article in articles:
                text = article.get_text(separator="\n", strip=True)
                if text:
                    content_texts.append(text)
        else:
            # Fallback to <p> tags
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if text:
                    content_texts.append(text)
                    
        clean_text = "\n\n".join(content_texts)
        
        # Return clean dictionary
        return {
            "title": title.strip() if title else "",
            "description": meta_desc.strip() if meta_desc else "",
            "content": clean_text[:5000] # Cap size
        }

    # Explicitly block unsafe methods (Hardcode enforcement)
    def post_data(self, *args, **kwargs):
        raise NotImplementedError("POST method is strictly disabled for security.")
        
    def put_data(self, *args, **kwargs):
        raise NotImplementedError("PUT method is strictly disabled for security.")
        
    def delete_data(self, *args, **kwargs):
        raise NotImplementedError("DELETE method is strictly disabled for security.")
