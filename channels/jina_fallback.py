import json
import httpx
from channels.base import BaseChannel
from core.logger import get_logger

logger = get_logger(__name__)

class JinaFallbackChannel(BaseChannel):
    """
    Fallback backend using free Jina Reader API.
    Converts any URL to markdown format.
    """
    
    def fetch(self, url: str, timeout: int = 15) -> str:
        """
        Fetch URL via Jina Reader.
        """
        jina_url = f"https://r.jina.ai/{url}"
        logger.info("JinaFallbackChannel fetching: %s", jina_url)
        
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(jina_url)
                response.raise_for_status()
                
                # Jina returns markdown directly
                markdown_content = response.text
                
                result = {
                    "source": "jina_fallback",
                    "content": markdown_content
                }
                return json.dumps(result, ensure_ascii=False)
                
        except Exception as exc:
            logger.warning("JinaFallbackChannel failed: %s", exc)
            # Returning string to indicate failure
            error_result = {
                "source": "jina_fallback",
                "error": str(exc)
            }
            return json.dumps(error_result, ensure_ascii=False)

    def ping(self) -> tuple[bool, str]:
        return True, "JinaFallbackChannel ready"
