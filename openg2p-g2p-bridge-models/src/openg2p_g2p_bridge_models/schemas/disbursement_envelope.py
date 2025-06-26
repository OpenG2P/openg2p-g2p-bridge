import datetime
from typing import List, Optional

from openg2p_g2pconnect_common_lib.schemas import Request, SyncResponse
from pydantic import BaseModel

from ..models import (
    DisbursementFrequency,
    BenefitType,
    CashDistributionMode,
    CancellationStatus,
)


class DisbursementEnvelopePayload(BaseModel):
    id: Optional[str] = None
    disbursement_envelope_id: Optional[str] = None
    benefit_program_mnemonic: Optional[str] = None
    target_registry: Optional[str] = None
    benefit_code_id: Optional[str] = None
    benefit_code_mnemonic: Optional[str] = None
    benefit_type: Optional[BenefitType] = None
    cash_distribution_mode: Optional[CashDistributionMode] = None
    disbursement_cycle_id: Optional[str] = None
    disbursement_frequency: Optional[DisbursementFrequency] = None
    cycle_code_mnemonic: Optional[str] = None
    number_of_beneficiaries: Optional[int] = None
    number_of_disbursements: Optional[int] = None
    total_disbursement_quantity: Optional[float] = None
    measurement_unit: Optional[str] = None
    disbursement_schedule_date: Optional[datetime.date] = None
    receipt_time_stamp: Optional[datetime.datetime] = None
    cancellation_status: Optional[CancellationStatus] = None
    cancellation_timestamp: Optional[datetime.datetime] = None


class DisbursementEnvelopeRequest(Request):
    message: List[DisbursementEnvelopePayload]


class DisbursementEnvelopeResponse(SyncResponse):
    message: Optional[List[DisbursementEnvelopePayload]] = None
