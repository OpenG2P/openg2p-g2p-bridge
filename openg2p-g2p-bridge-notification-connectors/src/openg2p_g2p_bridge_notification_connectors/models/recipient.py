from pydantic import BaseModel
from typing import Optional

class Recipient(BaseModel):
    recipient_id: str
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None 