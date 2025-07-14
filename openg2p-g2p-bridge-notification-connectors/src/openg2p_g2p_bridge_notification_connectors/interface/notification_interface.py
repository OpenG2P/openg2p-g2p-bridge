from abc import ABC, abstractmethod
from typing import List, Any
from ..models import Recipient, NotificationType

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