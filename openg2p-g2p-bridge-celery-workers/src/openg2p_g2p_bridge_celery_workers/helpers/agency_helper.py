
import logging
from sqlalchemy.orm import sessionmaker
from openg2p_g2p_bridge_models.schemas import AgencyDetailForPayment
from openg2p_fastapi_common.service import BaseService

from ..app import get_engine
_logger = logging.getLogger("openg2p_g2p_bridge")
_engine = get_engine()

class AgencyHelper(BaseService):
    def retrieve_agency_details(self, agency_id: str, benefit_program_id: str, benefit_code_id: str) -> AgencyDetailForPayment:
        """
        Retrieve the agency financial address details.
        """
        pbms_session_maker = sessionmaker(
            bind=_engine.get("db_engine_pbms"), expire_on_commit=False
        )
        with pbms_session_maker() as session:
            agency = (
                session.query() # TODO: Fetch Agency Details from PBMS
            )

            if not agency:
                _logger.error(f"No financial address found for agency {agency_id}")
                return None

            agency_detail_for_payment:AgencyDetailForPayment = AgencyDetailForPayment(
                agency_name=agency.agency_name, # TODO: Cross check
                agency_account_number=agency.bank_account_number,
                agency_account_type=agency.bank_account_type,
                agency_account_branch_code=agency.branch_code,
                agency_account_bank_code=agency.bank_code,
                agency_email_address=agency.email_address,
                agency_phone_number=agency.phone_number
            )
            return agency_detail_for_payment

