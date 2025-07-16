import enum
from pydantic import BaseModel
from typing import Optional

class NotificationType(enum.Enum):
    AGENCY_NOTIFICATION = "AGENCY_NOTIFICATION"
    WAREHOUSE_NOTIFICATION = "WAREHOUSE_NOTIFICATION"
    BENEFICIARY_NOTIFICATION = "BENEFICIARY_NOTIFICATION"

class NotificationResponseStatus(enum.Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"

class NotificationResponse(BaseModel):
    notification_id: str
    response: Optional[str] = None
    status: NotificationResponseStatus