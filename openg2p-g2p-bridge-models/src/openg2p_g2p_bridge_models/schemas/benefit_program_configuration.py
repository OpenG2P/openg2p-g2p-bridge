from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from openg2p_g2pconnect_common_lib.schemas import Request, SyncResponse

class BenefitProgramConfigurationPayload(BaseModel):
    benefit_program_mnemonic: str
    benefit_program_name: str
    funding_org_code: str
    funding_org_name: str
    sponsor_bank_code: str
    sponsor_bank_account_number: str
    sponsor_bank_branch_code: str
    sponsor_bank_account_currency: str
    id_mapper_resolution_required: bool = True


class BenefitProgramConfigurationRequest(Request):
    message: BenefitProgramConfigurationPayload

class BenefitProgramConfigurationResponse(SyncResponse):
    message: Optional[BenefitProgramConfigurationPayload] = None


