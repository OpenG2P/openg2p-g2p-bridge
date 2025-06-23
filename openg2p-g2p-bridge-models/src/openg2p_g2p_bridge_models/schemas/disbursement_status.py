import datetime
from enum import Enum
from typing import List, Optional

from openg2p_g2pconnect_common_lib.schemas import Request, SyncResponse
from pydantic import BaseModel

from ..errors.codes import G2PBridgeErrorCodes
from ..models import FundsAvailableWithBankEnum, FundsBlockedWithBankEnum


class DisbursementStatusRequest(Request):
    message: List[str]

class DisbursementReconPayload(BaseModel):
    bank_disbursement_batch_id: str
    disbursement_id: str
    disbursement_envelope_id: Optional[str] = None
    beneficiary_name_from_bank: Optional[str] = None

    remittance_reference_number: Optional[str] = None
    remittance_statement_id: Optional[str] = None
    remittance_statement_number: Optional[str] = None
    remittance_statement_sequence: Optional[str] = None
    remittance_entry_sequence: Optional[str] = None
    remittance_entry_date: Optional[datetime.datetime] = None
    remittance_value_date: Optional[datetime.datetime] = None

    reversal_found: Optional[bool] = None
    reversal_statement_id: Optional[str] = None
    reversal_statement_number: Optional[str] = None
    reversal_statement_sequence: Optional[str] = None
    reversal_entry_sequence: Optional[str] = None
    reversal_entry_date: Optional[datetime.datetime] = None
    reversal_value_date: Optional[datetime.datetime] = None
    reversal_reason: Optional[str] = None


class DisbursementErrorReconPayload(BaseModel):
    statement_id: Optional[str] = None
    statement_number: Optional[str] = None
    statement_sequence: Optional[str] = None
    entry_sequence: Optional[str] = None
    entry_date: Optional[datetime.datetime] = None
    value_date: Optional[datetime.datetime] = None
    error_reason: Optional[G2PBridgeErrorCodes] = None
    disbursement_id: str
    bank_reference_number: Optional[str] = None


class DisbursementReconRecords(BaseModel):
    disbursement_recon_payloads: Optional[List[DisbursementReconPayload]] = None
    disbursement_error_recon_payloads: Optional[
        List[DisbursementErrorReconPayload]
    ] = None


class DisbursementStatusPayload(BaseModel):
    disbursement_id: str
    disbursement_recon_records: Optional[DisbursementReconRecords] = None


class DisbursementStatusResponse(SyncResponse):
    message: Optional[List[DisbursementStatusPayload]] = None


class DisbursementEnvelopeStatusRequest(Request):
    message: str

class DisbursementEnvelopeBatchStatusPayload(BaseModel):
    disbursement_envelope_id: str
    benefit_code_id: Optional[str] = None
    benefit_code_mnemonic: Optional[str] = None
    benefit_type: Optional[str] = None
    number_of_beneficiaries_received: Optional[int] = None
    number_of_beneficiaries_declared: Optional[int] = None
    number_of_disbursements_declared: Optional[int] = None
    number_of_disbursements_received: int
    total_disbursement_quantity_declared: Optional[float] = None
    total_disbursement_quantity_received: int

class DistributionDetailsForEnvelope(BaseModel):
    administrative_zone_id_large: Optional[str] = None
    administrative_zone_mnemonic_large: Optional[str] = None
    administrative_zone_id_small: Optional[str] = None
    administrative_zone_mnemonic_small: Optional[str] = None
    warehouse_id: Optional[str] = None
    warehouse_mnemonic: Optional[str] = None
    agency_id: Optional[str] = None
    agency_mnemonic: Optional[str] = None
    number_of_beneficiaries: Optional[int] = None
    total_disbursement_quantity: Optional[float] = None
    warehouse_notified: Optional[bool] = None
    agency_notified: Optional[bool] = None
    no_of_pods_received: Optional[int] = None

class EnvelopeStatusForPhysicalBenefitsPayload(DisbursementEnvelopeBatchStatusPayload):
    cash_distribution_mode: Optional[str] = None
    no_of_warehouses_allocated: Optional[int] = None
    no_of_warehouses_notified: Optional[int] = None
    no_of_agencies_allocated: Optional[int] = None
    no_of_agencies_notified: Optional[int] = None
    no_of_beneficiaries_notified: Optional[int] = None
    no_of_pods_received: Optional[int] = None
    disbursement_details_for_envelope: Optional[List[DistributionDetailsForEnvelope]] = None
       
class EnvelopeStatusForDigitalCashPayload(DisbursementEnvelopeBatchStatusPayload):

    funds_available_with_bank: FundsAvailableWithBankEnum
    funds_available_latest_timestamp: Optional[datetime.datetime] = None
    funds_available_latest_error_code: Optional[str] = None
    funds_available_attempts: int

    funds_blocked_with_bank: FundsBlockedWithBankEnum
    funds_blocked_latest_timestamp: Optional[datetime.datetime] = None
    funds_blocked_latest_error_code: Optional[str] = None
    funds_blocked_attempts: int
    funds_blocked_reference_number: Optional[str] = None

    id_mapper_resolution_required: Optional[bool] = None
    number_of_disbursements_shipped: int
    number_of_disbursements_reconciled: int
    number_of_disbursements_reversed: int


class DisbursementEnvelopeStatusResponse(SyncResponse):
    message: Optional[EnvelopeStatusForDigitalCashPayload|EnvelopeStatusForPhysicalBenefitsPayload] = None
