import datetime
from typing import List, Optional

from openg2p_g2pconnect_common_lib.schemas import Request, SyncResponse
from pydantic import BaseModel

from ..models import DisbursementCancellationStatus
from .disbursement_envelope import DisbursementBatchControlGeoPayload

class DisbursementPayload(BaseModel):
    disbursement_id: str
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
    disbursement_batch_control_id: Optional[str] = None
    message: List[DisbursementPayload]


class DisbursementResponse(SyncResponse):
    disbursement_batch_control_id: Optional[str] = None
    message: Optional[List[DisbursementPayload]] = None


class DisbursementBatchControlPayload(BaseModel):
    disbursement_batch_control_id: str
    disbursement_cycle_id: str
    disbursement_envelope_id: str
    fa_resolution_status: str
    fa_resolution_timestamp: Optional[datetime.datetime] = None
    fa_resolution_latest_error_code: Optional[str] = None
    fa_resolution_attempts: int
    sponsor_bank_dispatch_status: str
    sponsor_bank_dispatch_timestamp: Optional[datetime.datetime] = None
    sponsor_bank_dispatch_latest_error_code: Optional[str] = None
    sponsor_bank_dispatch_attempts: int
    geo_resolution_status: str
    geo_resolution_timestamp: Optional[datetime.datetime] = None
    geo_resolution_latest_error_code: Optional[str] = None
    geo_resolution_attempts: int
    warehouse_allocation_status: str
    warehouse_allocation_timestamp: Optional[datetime.datetime] = None
    warehouse_allocation_latest_error_code: Optional[str] = None
    warehouse_allocation_attempts: int
    agency_allocation_status: str
    agency_allocation_timestamp: Optional[datetime.datetime] = None
    agency_allocation_latest_error_code: Optional[str] = None
    agency_allocation_attempts: int
    disbursement_batch_control_geos: Optional[List[DisbursementBatchControlGeoPayload]] = None

class DisbursementBatchControlRequest(Request):
    disbursement_batch_control_id: str

class DisbursementBatchControlResponse(SyncResponse):
    message: Optional[DisbursementBatchControlPayload] = None