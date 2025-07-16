import logging
from sqlalchemy.orm import sessionmaker
from openg2p_g2p_bridge_models.schemas import SponsorBankConfiguration
from openg2p_fastapi_common.service import BaseService


from ..app import get_engine
_logger = logging.getLogger("openg2p_g2p_bridge")
_engine = get_engine()

class WarehouseHelper(BaseService):
    def retrieve_sponsor_bank_configuration(
        benefit_program_id: str, benefit_code_id: str
    ) -> SponsorBankConfiguration:
        """
        Retrieve the sponsor bank configuration for the given benefit program and code.
        """
        pbms_session_maker = sessionmaker(
            bind=_engine.get("db_engine_pbms"), expire_on_commit=False
        )
        with pbms_session_maker() as session:
            sponsor_bank_configuration = (
                session.query()
            )

            if not sponsor_bank_configuration:
                _logger.error(
                    f"No SponsorBankConfiguration found for program {benefit_program_id} and code {benefit_code_id}"
                )
                return None
            sponsor_bank_configuration = SponsorBankConfiguration(
                program_account_number=sponsor_bank_configuration.program_account_number,
                program_account_type=sponsor_bank_configuration.program_account_type,
                program_account_branch_code=sponsor_bank_configuration.program_account_branch_code,
                sponsor_bank_code=sponsor_bank_configuration.sponsor_bank_code,
            )

            return sponsor_bank_configuration

def retrieve_sponsor_bank_configuration(
    account_number:str
) -> SponsorBankConfiguration:
    """
    Retrieve the sponsor bank configuration for the given benefit program and code.
    """
    pbms_session_maker = sessionmaker(
        bind=_engine.get("db_engine_pbms"), expire_on_commit=False
    )
    with pbms_session_maker() as session:
        sponsor_bank_configuration = (
            session.query()
        )

        if not sponsor_bank_configuration:
            _logger.error(
                f"No SponsorBankConfiguration found"
            )
            return None
        sponsor_bank_configuration = SponsorBankConfiguration(
            program_account_number=sponsor_bank_configuration.program_account_number,
            program_account_type=sponsor_bank_configuration.program_account_type,
            program_account_branch_code=sponsor_bank_configuration.program_account_branch_code,
            sponsor_bank_code=sponsor_bank_configuration.sponsor_bank_code,
        )

        return sponsor_bank_configuration