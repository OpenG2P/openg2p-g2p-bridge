from typing import List, Any

from novu.api import EventApi, SubscriberApi
from novu.dto import SubscriberDto

from ..interface.notification_interface import NotificationInterface
from ..models.recipient import Recipient
from ..config import Settings

_config = Settings.get_config()


class NovuNotifier(NotificationInterface):
    def __init__(self) -> None:
        self.event_api = EventApi(_config.novu_url, _config.novu_api_key)
        self.subscriber_api = SubscriberApi(_config.novu_url, _config.novu_api_key)

    def send_notification(
        self,
        notification_id: str,
        payload: Any,
        notification_type: str,
        recipients: List[Recipient],
    ) -> None:
        # Create subscribers in Novu
        for recipient in recipients:
            subscriber_dto = SubscriberDto(
                subscriber_id=recipient.recipient_id,
                email=recipient.recipient_email,
                phone=recipient.recipient_phone,
            )
            self.subscriber_api.create(subscriber_dto)

        # Get recipient IDs
        recipient_ids = [r.recipient_id for r in recipients]

        # Trigger the notification
        self.event_api.trigger(
            name=notification_id,
            recipients=recipient_ids,
            payload=payload,
        )
