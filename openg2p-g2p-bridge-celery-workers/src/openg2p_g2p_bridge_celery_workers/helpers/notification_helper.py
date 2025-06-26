import logging
from typing import Optional

import httpx
from openg2p_fastapi_common.service import BaseService
from openg2p_g2p_bridge_models.schemas.notification import NotificationRequest

from ..config import Settings

_config = Settings.get_config()
_logger = logging.getLogger(_config.logging_default_logger_name)


class NotificationHelper(BaseService):
    async def send_notification(
        self,
        url: str,
        notification_request: NotificationRequest,
        timeout: Optional[float] = 10.0,
    ) -> httpx.Response:
        """
        Asynchronous notification sender for use in async contexts.
        Accepts a NotificationRequest Pydantic object and serializes it.
        """
        payload = notification_request.model_dump()
        _logger.info(f"Sending async notification to {url} with payload: {payload}")
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                _logger.info(
                    f"Async notification sent successfully. Status: {response.status_code}"
                )
                return response
        except Exception as e:
            _logger.error(f"Async notification failed: {e}")
            raise
