import datetime
from typing import List, Optional

from openg2p_g2pconnect_common_lib.schemas import Request, SyncResponse
from pydantic import BaseModel

from ..models import DisbursementCancellationStatus


class DisbursementPayload(BaseModel):
    id: Optional[str] = None
    mis_reference_number: Optional[str] = None
    disbursement_id: Optional[str] = None
    disbursement_envelope_id: Optional[str] = None
    beneficiary_id: Optional[str] = None
    beneficiary_name: Optional[str] = None
    disbursement_quantity: Optional[float] = None
    narrative: Optional[str] = None
    receipt_time_stamp: Optional[datetime.datetime] = None
    cancellation_status: Optional[DisbursementCancellationStatus] = None
    cancellation_time_stamp: Optional[datetime.datetime] = None
    disbursement_cycle_id: Optional[str] = None
    disbursement_batch_control_id: Optional[str] = None
    response_error_codes: Optional[List[str]] = None


class DisbursementRequest(Request):
    message: List[DisbursementPayload]


class DisbursementResponse(SyncResponse):
    message: Optional[List[DisbursementPayload]] = None
