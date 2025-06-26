import enum
from datetime import datetime

from openg2p_fastapi_common.models import BaseORMModelWithTimes
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class NotificationStatus(enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    PROCESSED = "PROCESSED"
    ERROR = "ERROR"


class NotificationLog(BaseORMModelWithTimes):
    __tablename__ = "notification_logs"
    notification_id: Mapped[str] = mapped_column(String, unique=True)
    notification_type: Mapped[str] = mapped_column(String, index=True)
    recipient: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String, default=NotificationStatus.PENDING.value, index=True
    )
    response: Mapped[str] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
