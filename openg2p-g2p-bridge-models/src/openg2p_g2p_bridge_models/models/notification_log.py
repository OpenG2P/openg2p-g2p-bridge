import enum
from datetime import datetime

from .base import BaseORMModelWithId
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class NotificationLog(BaseORMModelWithId):
    __tablename__ = "notification_logs"
    notification_type: Mapped[str] = mapped_column(String, index=True)
    recipient: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
