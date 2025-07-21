from abc import ABC, abstractmethod
from typing import Any

from ..models import NotificationType, Recipient


class NotificationInterface(ABC):
    @abstractmethod
    def send_notification(
        self,
        notification_id: str,
        payload: Any,
        notification_type: NotificationType,
        recipient: Recipient,
    ) -> None:
        """
        Send a notification to a list of recipients.
        """
        pass
