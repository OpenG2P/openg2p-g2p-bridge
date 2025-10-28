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
    g2p_pagination_request: Optional[G2PPaginationRequest] = None
    g2p_request_payload: Optional[dict] = None


class DisbursementRequest(BaseModel):
    g2p_request_header: G2PRequestHeader
    g2p_request_body: Optional[DisbursementRequestBody] = None


class DisbursementResponse(BaseModel):
    g2p_response_header: G2PResponseHeader
    g2p_response_body: "DisbursementResponseBody"


class DisbursementResponseBody(BaseModel):
    g2p_pagination_response: Optional[G2PPaginationResponse] = None
    g2p_response_payload: List[Disbursement]


class DisbursementSummaryRequestBody(BaseModel):
    g2p_request_payload: Optional[dict] = None


class DisbursementSummaryRequest(BaseModel):
    g2p_request_header: G2PRequestHeader
    g2p_request_body: Optional[DisbursementSummaryRequestBody] = None


class DisbursementSummaryResponse(BaseModel):
    g2p_response_header: G2PResponseHeader
    g2p_response_body: "DisbursementSummaryResponseBody"


class DisbursementSummaryResponseBody(BaseModel):
    g2p_response_payload: List[DisbursementSummary]
