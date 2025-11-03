from enum import Enum


from enum import Enum
from typing import Optional

from pydantic import AliasChoices, BaseModel, Field

# TODO: These will be updated in the future to match G2P Request Response specs


class StatusEnum(Enum):
    rcvd = "rcvd"
    pdng = "pdng"
    succ = "succ"
    rjct = "rjct"


class SyncResponseStatusReasonCodeEnum(Enum):
    rjct_version_invalid = "rjct.version.invalid"
    rjct_message_id_duplicate = "rjct.message_id.duplicate"
    rjct_message_ts_invalid = "rjct.message_ts.invalid"
    rjct_action_invalid = "rjct.action.invalid"
    rjct_action_not_supported = "rjct.action.not_supported"
    rjct_total_count_invalid = "rjct.total_count.invalid"
    rjct_total_count_limit_exceeded = "rjct.total_count.limit_exceeded"
    rjct_errors_too_many = "rjct.errors.too_many"
    rjct_jwt_invalid = "rjct.jwt.invalid"
    rjct_file_size_exceeded = "rjct.file.size.exceeded"
    rjct_file_type_invalid = "rjct.file.type.invalid"
    rjct_virus_check_failed = "rjct.virus.check.failed"


class SyncResponseHeader(BaseModel):
    version: Optional[str] = "1.0.0"
    message_id: str
    message_ts: str
    action: str
    status: StatusEnum
    status_reason_code: Optional[SyncResponseStatusReasonCodeEnum] = None
    status_reason_message: Optional[str] = ""
    total_count: Optional[int] = None
    completed_count: Optional[int] = None
    sender_id: Optional[str] = None
    receiver_id: Optional[str] = None
    is_msg_encrypted: Optional[bool] = Field(
        validation_alias=AliasChoices("is_msg_encrypted", "is_encrypted"), default=False
    )
    meta: Optional[dict] = {}


class SyncResponse(BaseModel):
    header: SyncResponseHeader
    message: object


class RequestHeader(BaseModel):
    version: Optional[str] = "1.0.0"
    message_id: str
    message_ts: str
    action: str
    sender_id: str
    sender_uri: Optional[str] = ""
    receiver_id: Optional[str] = ""
    total_count: int
    is_msg_encrypted: Optional[bool] = Field(
        validation_alias=AliasChoices("is_msg_encrypted", "is_encrypted"), default=False
    )
    meta: Optional[object] = None


class Request(BaseModel):
    header: RequestHeader
    message: object
