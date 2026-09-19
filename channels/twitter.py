"""
channels/twitter.py — Twitter / X.com channel specialized parser
=================================================================
This channel fetches Twitter pages using the SecureFetcherChannel to guarantee
absolute security, RAM-only cookies, and strict GET requests. 
It then parses specific Twitter elements like tweetText, User-Name, and time.
"""

from __future__ import annotations

import json
from bs4 import BeautifulSoup

from channels.secure_fetcher import SecureFetcherChannel
from core.logger import get_logger

logger = get_logger(__name__)

class TwitterChannel(SecureFetcherChannel):
    """
    Fetches Twitter/X using secure local cookies and parses specific DOM elements.
    """

    def fetch(self, url: str, timeout: int = 15) -> str:
        """
        Fetch data from the given Twitter URL securely and parse specifically.
        Returns JSON string representation.
        """
        # 1. Gunakan SecureFetcher (parent class) untuk mengambil HTML (Tidak melakukan request sendiri)
        html_content = self._fetch_raw_html(url, timeout)
        
        # Jika balikan adalah JSON string error (misalnya karena tidak ada library), kembalikan langsung
        if html_content.startswith('{"error"'):
            return html_content

        # 2. Lakukan parsing spesifik untuk Twitter
        parsed_data = self._parse_twitter_html(html_content)
        return json.dumps(parsed_data, ensure_ascii=False)

    def _parse_twitter_html(self, html: str) -> dict:
        """
        Extract specific Twitter elements:
        1. Teks cuitan utama (data-testid="tweetText")
        2. Nama/Handle pengguna (data-testid="User-Name")
        3. Waktu/Tanggal (<time>)
        """
        soup = BeautifulSoup(html, "html.parser")
        
        try:
            # 1. Extract tweet text
            tweet_text = ""
            tweet_tag = soup.find(attrs={"data-testid": "tweetText"})
            if tweet_tag:
                tweet_text = tweet_tag.get_text(separator="\n", strip=True)
            
            # 2. Extract user name/handle
            user_name = ""
            user_tag = soup.find(attrs={"data-testid": "User-Name"})
            if user_tag:
                user_name = user_tag.get_text(separator=" | ", strip=True)
                
            # 3. Extract time/date
            tweet_time = ""
            time_tag = soup.find("time")
            if time_tag:
                if time_tag.has_attr("datetime"):
                    tweet_time = time_tag["datetime"]
                else:
                    tweet_time = time_tag.get_text(strip=True)
            
            # Jika struktur tidak ditemukan, kembalikan info tanpa memunculkan error traceback
            if not tweet_text and not user_name and not tweet_time:
                title = soup.title.string.strip() if soup.title else ""
                return {
                    "info": "Halaman berhasil diambil, tetapi struktur spesifik Twitter (tweetText, User-Name, time) tidak ditemukan. Halaman mungkin belum ter-render utuh oleh JS.",
                    "raw_title": title
                }
                
            return {
                "tweet_text": tweet_text,
                "user_name": user_name,
                "time": tweet_time
            }
            
        except Exception as e:
            logger.warning("Failed to parse Twitter HTML: %s", str(e))
            return {
                "info": "Terjadi kesalahan saat memparsing struktur DOM Twitter.",
                "error_detail": str(e)
            }
