import logging
import httpx
from typing import Any, Dict, Optional

from openg2p_fastapi_common.service import BaseService
from ..config import Settings

_config = Settings.get_config()
_logger = logging.getLogger(_config.logging_default_logger_name)

class NotificationHelper(BaseService):
    async def send_notification(self, url: str, payload: Dict[str, Any], timeout: Optional[float] = 10.0) -> httpx.Response:
        """
        Asynchronous notification sender for use in async contexts.
        """
        _logger.info(f"Sending async notification to {url} with payload: {payload}")
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                _logger.info(f"Async notification sent successfully. Status: {response.status_code}")
                return response
        except Exception as e:
            _logger.error(f"Async notification failed: {e}")
            raise 