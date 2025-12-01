from datetime import date, datetime
from typing import List, Optional

from openg2p_fastapi_common.schemas import (
    G2PRequestHeader,
    G2PResponseHeader,
    G2PPaginationRequest,
    G2PPaginationResponse,
)
from pydantic import BaseModel


class Disbursement(BaseModel):
    disbursement_id: str
    disbursement_envelope_id: Optional[str] = None
    program_mnemonic: str
    cycle_code_mnemonic: str
    disbursement_quantity: float
    benefit_code: str
    benefit_type: str
    agency_mnemonic: str
    measurement_unit: str
    disbursement_schedule_date: date


class DisbursementSummary(BaseModel):
    benefit_code_mnemonic: str
    benefit_type: str  # TODO: Add ENUM
    measurement_unit: str
    total_quantity_received: float


class DisbursementRequestBody(BaseModel):
    pagination_request: Optional[G2PPaginationRequest] = None
    request_payload: Optional[dict] = None


class DisbursementRequest(BaseModel):
    request_header: G2PRequestHeader
    request_body: Optional[DisbursementRequestBody] = None


class DisbursementResponse(BaseModel):
    response_header: G2PResponseHeader
    response_body: "DisbursementResponseBody"


class DisbursementResponseBody(BaseModel):
    pagination_response: Optional[G2PPaginationResponse] = None
    response_payload: List[Disbursement]


class DisbursementSummaryRequestBody(BaseModel):
    equest_payload: Optional[dict] = None


class DisbursementSummaryRequest(BaseModel):
    request_header: G2PRequestHeader
    request_body: Optional[DisbursementSummaryRequestBody] = None


class DisbursementSummaryResponse(BaseModel):
    response_header: G2PResponseHeader
    response_body: "DisbursementSummaryResponseBody"


class DisbursementSummaryResponseBody(BaseModel):
    response_payload: List[DisbursementSummary]