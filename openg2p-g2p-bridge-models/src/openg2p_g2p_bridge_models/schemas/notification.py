import datetime
import enum
from typing import List, Optional

from openg2p_g2pconnect_common_lib.schemas import Request, SyncResponse
from pydantic import BaseModel

class NotificationType(enum.Enum):
    AGENCY_NOTIFICATION = "AGENCY_NOTIFICATION"
    WAREHOUSE_NOTIFICATION = "WAREHOUSE_NOTIFICATION"
    BENEFICIARY_NOTIFICATION = "BENEFICIARY_NOTIFICATION"

class WarehouseNotificationPayload(BaseModel):
    program_mnemonic: Optional[str] = None
    program_description: Optional[str] = None
    target_registry: Optional[str] = None
    disbursement_cycle_mnemonic: Optional[str] = None
    disbursement_date: Optional[datetime.datetime] = None
    benefit_code_id: Optional[str] = None
    benefit_code_mnemonic: Optional[str] = None
    benefit_type: Optional[str] = None
    measurement_unit: Optional[str] = None
    benefit_description: Optional[str] = None
    warehouse_id: Optional[str] = None
    warehouse_mnemonic: Optional[str] = None
    agency_id: Optional[str] = None
    agency_mnemonic: Optional[str] = None
    agency_description: Optional[str] = None
    total_quantity: Optional[float] = None
    no_of_bebeficiaries: Optional[int] = None
    administrative_zone_id_large: Optional[str] = None
    administrative_zone_mnemonic_large: Optional[str] = None
    administrative_zone_id_small: Optional[str] = None
    administrative_zone_mnemonic_small: Optional[str] = None

class BeneficiaryEntitlement(BaseModel):
    beneficiary_id: Optional[str] = None
    beneficiary_name: Optional[str] = None
    total_quantity: Optional[float] = None

class AgencyNotificationPayload(BaseModel):
    program_mnemonic: Optional[str] = None
    program_description: Optional[str] = None
    target_registry: Optional[str] = None
    disbursement_cycle_mnemonic: Optional[str] = None
    disbursement_date: Optional[datetime.datetime] = None
    benefit_code_id: Optional[str] = None
    benefit_code_mnemonic: Optional[str] = None
    benefit_type: Optional[str] = None
    measurement_unit: Optional[str] = None
    benefit_description: Optional[str] = None
    warehouse_id: Optional[str] = None
    warehouse_mnemonic: Optional[str] = None
    agency_id: Optional[str] = None
    agency_mnemonic: Optional[str] = None
    agency_description: Optional[str] = None
    total_quantity: Optional[float] = None
    no_of_bebeficiaries: Optional[int] = None
    administrative_zone_id_large: Optional[str] = None
    administrative_zone_mnemonic_large: Optional[str] = None
    administrative_zone_id_small: Optional[str] = None
    administrative_zone_mnemonic_small: Optional[str] = None
    beneficiary_entitlements: Optional[List[BeneficiaryEntitlement]] = None

class BeneficiaryNotificationPayload(BaseModel):
    program_mnemonic: Optional[str] = None
    program_description: Optional[str] = None
    target_registry: Optional[str] = None
    disbursement_cycle_mnemonic: Optional[str] = None
    disbursement_date: Optional[datetime.datetime] = None
    benefit_code_id: Optional[str] = None
    benefit_code_mnemonic: Optional[str] = None
    benefit_type: Optional[str] = None
    measurement_unit: Optional[str] = None
    benefit_description: Optional[str] = None
    warehouse_id: Optional[str] = None
    warehouse_mnemonic: Optional[str] = None
    agency_id: Optional[str] = None
    agency_mnemonic: Optional[str] = None
    agency_description: Optional[str] = None
    total_quantity: Optional[float] = None
    administrative_zone_id_large: Optional[str] = None
    administrative_zone_mnemonic_large: Optional[str] = None
    administrative_zone_id_small: Optional[str] = None
    administrative_zone_mnemonic_small: Optional[str] = None
    beneficiary_entitlement: Optional[BeneficiaryEntitlement] = None

    
