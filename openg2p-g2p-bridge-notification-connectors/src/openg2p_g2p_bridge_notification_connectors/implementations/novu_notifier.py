from typing import List, Any

import novu_py
from novu_py import Novu
from ..config import Settings
from ..interface.notification_interface import NotificationInterface
from ..models import Recipient, NotificationType, NotificationResponseStatus, NotificationResponse

_config = Settings.get_config()

class NovuNotifier(NotificationInterface):
    def send_notification(
        self,
        notification_id: str,
        payload: Any,
        notification_type: NotificationType,
        recipient: Recipient,
    ) -> NotificationResponse:
        
        workflow_id = None
        if notification_type == NotificationType.WAREHOUSE_NOTIFICATION.value:
            workflow_id = _config.novu_warehouse_workflow_id
        elif notification_type == NotificationType.AGENCY_NOTIFICATION.value:
            workflow_id = _config.novu_agency_workflow_id
        elif notification_type == NotificationType.BENEFICIARY_NOTIFICATION.value:
            workflow_id = _config.novu_beneficiary_workflow_id
        else:
            raise ValueError(f"Unsupported notification type: {notification_type}")
        
        with Novu(secret_key=_config.novu_api_key) as novu:
            novu_response = novu.trigger(trigger_event_request_dto=novu_py.TriggerEventRequestDto(
                workflow_id=workflow_id,
                payload=payload or {},
                to=recipient.recipient_email,
            ))
            notification_response = NotificationResponse(
                notification_id=notification_id,
                response=novu_response.message,
                status=NotificationResponseStatus.SUCCESS # TODO: check response from Novu
            )
            return notification_response
