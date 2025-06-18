import logging
from datetime import datetime

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService
from openg2p_g2p_bridge_models.errors.codes import G2PBridgeErrorCodes
from openg2p_g2p_bridge_models.errors.exceptions import DisbursementStatusException
from openg2p_g2p_bridge_models.models import (
    EnvelopeControl,
    EnvelopeBatchStatusForDigitalCash,
)
from openg2p_g2p_bridge_models.schemas import (
    DisbursementEnvelopeBatchStatusPayload,
    DisbursementEnvelopeStatusRequest,
    DisbursementEnvelopeStatusResponse,
    DisbursementStatusRequest,
)
from openg2p_g2pconnect_common_lib.schemas import (
    StatusEnum,
    SyncResponseHeader,
)
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select

from ..config import Settings

_config = Settings.get_config()
_logger = logging.getLogger(_config.logging_default_logger_name)


class DisbursementEnvelopeStatusService(BaseService):
    async def get_disbursement_envelope_batch_status(
        self, disbursement_envelope_status_request: DisbursementEnvelopeStatusRequest
    ) -> DisbursementEnvelopeBatchStatusPayload:
        _logger.info("Retrieving disbursement envelope status")
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            try:
                envelope_control = (
                    await session.execute(
                        select(EnvelopeControl).where(
                            EnvelopeControl.disbursement_envelope_id
                            == disbursement_envelope_status_request.message
                        )
                    )
                ).scalars().first()

                if not envelope_control:
                    raise DisbursementStatusException(
                        code=G2PBridgeErrorCodes.DISBURSEMENT_ENVELOPE_NOT_FOUND,
                        message="Disbursement envelope not found",
                    )
                
                digital_cash_status = (
                    await session.execute(
                        select(EnvelopeBatchStatusForDigitalCash).where(
                            EnvelopeBatchStatusForDigitalCash.disbursement_envelope_id
                            == disbursement_envelope_status_request.message
                        )
                    )
                ).scalars().first()

                return self.construct_batch_status_payload(envelope_control, digital_cash_status)
            except DisbursementStatusException as e:
                _logger.error("Error retrieving disbursement envelope status")
                raise e
    
    def construct_batch_status_payload(
        self,
        envelope_control: EnvelopeControl,
        digital_cash_status: EnvelopeBatchStatusForDigitalCash = None,
    ) -> DisbursementEnvelopeBatchStatusPayload:
        payload = {
            "disbursement_envelope_id": envelope_control.disbursement_envelope_id,
            "number_of_disbursements_received": envelope_control.number_of_disbursements_received,
            "total_disbursement_quantity_received": envelope_control.total_disbursement_quantity_received,
        }
        if digital_cash_status:
            payload.update(
                {
                    "funds_available_with_bank": digital_cash_status.funds_available_with_bank,
                    "funds_available_latest_timestamp": digital_cash_status.funds_available_latest_timestamp,
                    "funds_available_latest_error_code": digital_cash_status.funds_available_latest_error_code,
                    "funds_available_attempts": digital_cash_status.funds_available_attempts,
                    "funds_blocked_with_bank": digital_cash_status.funds_blocked_with_bank,
                    "funds_blocked_latest_timestamp": digital_cash_status.funds_blocked_latest_timestamp,
                    "funds_blocked_latest_error_code": digital_cash_status.funds_blocked_latest_error_code,
                    "funds_blocked_attempts": digital_cash_status.funds_blocked_attempts,
                    "funds_blocked_reference_number": digital_cash_status.funds_blocked_reference_number,
                    "number_of_disbursements_shipped": digital_cash_status.number_of_disbursements_shipped,
                    "number_of_disbursements_reconciled": digital_cash_status.number_of_disbursements_reconciled,
                    "number_of_disbursements_reversed": digital_cash_status.number_of_disbursements_reversed,
                }
            )
        return DisbursementEnvelopeBatchStatusPayload(**payload)

    async def construct_disbursement_envelope_status_error_response(
        self,
        disbursement_status_request: DisbursementStatusRequest,
        code: str,
    ) -> DisbursementEnvelopeStatusResponse:
        response = DisbursementEnvelopeStatusResponse(
            header=SyncResponseHeader(
                message_id=disbursement_status_request.header.message_id,
                message_ts=datetime.now().isoformat(),
                action=disbursement_status_request.header.action,
                status=StatusEnum.rjct,
                status_reason_message=code,
            ),
            message=None,
        )

        return response

    async def construct_disbursement_envelope_status_success_response(
        self,
        disbursement_status_request: DisbursementStatusRequest,
        disbursement_envelope_batch_status_payload: DisbursementEnvelopeBatchStatusPayload,
    ) -> DisbursementEnvelopeStatusResponse:
        response = DisbursementEnvelopeStatusResponse(
            header=SyncResponseHeader(
                message_id=disbursement_status_request.header.message_id,
                message_ts=datetime.now().isoformat(),
                action=disbursement_status_request.header.action,
                status=StatusEnum.succ,
            ),
            message=disbursement_envelope_batch_status_payload,
        )
        return response
