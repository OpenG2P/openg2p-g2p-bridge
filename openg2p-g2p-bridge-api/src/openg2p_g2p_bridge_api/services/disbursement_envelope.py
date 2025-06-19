import logging
import uuid
from datetime import datetime

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService
from openg2p_g2p_bridge_models.errors.codes import G2PBridgeErrorCodes
from openg2p_g2p_bridge_models.errors.exceptions import DisbursementEnvelopeException
from openg2p_g2p_bridge_models.models import (
    BenefitProgramConfiguration,
    CancellationStatus,
    DisbursementEnvelope,
    EnvelopeControl,
    EnvelopeBatchStatusForDigitalCash,
    DisbursementFrequency,
    FundsAvailableWithBankEnum,
    FundsBlockedWithBankEnum,
    BenefitType,
    CashDistributionMode,
)
from openg2p_g2p_bridge_models.schemas import (
    DisbursementEnvelopePayload,
    DisbursementEnvelopeRequest,
    DisbursementEnvelopeResponse,
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


class DisbursementEnvelopeService(BaseService):
    async def create_disbursement_envelopes(
        self, disbursement_envelope_request: DisbursementEnvelopeRequest
    ) -> list[DisbursementEnvelopePayload]:
        _logger.info("Bulk creating disbursement envelopes")
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        disbursement_envelopes: list[DisbursementEnvelope] = []
        envelope_controls: list[EnvelopeControl] = []
        envelope_batch_statuses: list[EnvelopeBatchStatusForDigitalCash] = []
        disbursement_envelope_payloads: list[DisbursementEnvelopePayload] = disbursement_envelope_request.message
        async with session_maker() as session:
            for disbursement_envelope_payload in disbursement_envelope_payloads:
                try:
                    await self.validate_envelope_payload(disbursement_envelope_payload)
                except DisbursementEnvelopeException as e:
                    raise e
                disbursement_envelope = await self.construct_disbursement_envelope(
                    disbursement_envelope_payload=disbursement_envelope_payload
                )
                disbursement_envelope_payload.disbursement_envelope_id = disbursement_envelope.disbursement_envelope_id
                disbursement_envelopes.append(disbursement_envelope)

                envelope_control = await self.construct_envelope_control(disbursement_envelope)
                envelope_controls.append(envelope_control)

                if disbursement_envelope.benefit_type == BenefitType.CASH and disbursement_envelope.cash_distribution_mode == CashDistributionMode.DIGITAL:
                    batch_status = await self.construct_envelope_batch_status_for_digital_cash(
                        disbursement_envelope, session
                    )
                    envelope_batch_statuses.append(batch_status)
            session.add_all(disbursement_envelopes)
            session.add_all(envelope_controls)
            session.add_all(envelope_batch_statuses)
            await session.commit()
        _logger.info("Bulk disbursement envelopes created successfully")
        return disbursement_envelope_payloads

    async def cancel_disbursement_envelope(
        self, disbursement_envelope_request: DisbursementEnvelopeRequest
    ) -> DisbursementEnvelopePayload:
        _logger.info("Cancelling disbursement envelope")
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            disbursement_envelope_payload: DisbursementEnvelopePayload = (
                disbursement_envelope_request.message
            )
            disbursement_envelope_id: str = (
                disbursement_envelope_payload.disbursement_envelope_id
            )

            disbursement_envelope: DisbursementEnvelope = (
                await session.execute(
                    select(DisbursementEnvelope).where(
                        DisbursementEnvelope.disbursement_envelope_id
                        == disbursement_envelope_id
                    )
                )
            ).scalar()

            if disbursement_envelope is None:
                _logger.error(
                    f"Disbursement envelope with ID {disbursement_envelope_id} not found"
                )
                raise DisbursementEnvelopeException(
                    G2PBridgeErrorCodes.DISBURSEMENT_ENVELOPE_NOT_FOUND
                )

            if (
                disbursement_envelope.cancellation_status
                == CancellationStatus.CANCELLED.value
            ):
                _logger.error(
                    f"Disbursement envelope with ID {disbursement_envelope_id} already cancelled"
                )
                raise DisbursementEnvelopeException(
                    G2PBridgeErrorCodes.DISBURSEMENT_ENVELOPE_ALREADY_CANCELED
                )

            disbursement_envelope.cancellation_status = (
                CancellationStatus.CANCELLED.value
            )
            disbursement_envelope.cancellation_timestamp = datetime.now()

            await session.commit()
            _logger.info("Disbursement envelope cancelled successfully")
            return disbursement_envelope_payload

    async def construct_disbursement_envelope_success_response(
        self,
        disbursement_envelope_request: DisbursementEnvelopeRequest,
        disbursement_envelope_payloads: list[DisbursementEnvelopePayload],
    ) -> DisbursementEnvelopeResponse:
        _logger.info("Constructing disbursement envelope success response")
        disbursement_envelope_response: DisbursementEnvelopeResponse = (
            DisbursementEnvelopeResponse(
                header=SyncResponseHeader(
                    message_id=disbursement_envelope_request.header.message_id,
                    message_ts=datetime.now().isoformat(),
                    action=disbursement_envelope_request.header.action,
                    status=StatusEnum.succ,
                ),
                message=disbursement_envelope_payloads,
            )
        )
        _logger.info("Disbursement envelope success response constructed")
        return disbursement_envelope_response

    async def construct_disbursement_envelope_error_response(
        self,
        disbursement_envelope_request: DisbursementEnvelopeRequest,
        error_code: G2PBridgeErrorCodes,
    ) -> DisbursementEnvelopeResponse:
        _logger.error("Constructing disbursement envelope error response")
        disbursement_envelope_response: DisbursementEnvelopeResponse = (
            DisbursementEnvelopeResponse(
                header=SyncResponseHeader(
                    message_id=disbursement_envelope_request.header.message_id,
                    message_ts=datetime.now().isoformat(),
                    action=disbursement_envelope_request.header.action,
                    status=StatusEnum.rjct,
                    status_reason_message=error_code.value,
                ),
                message=[],
            )
        )
        _logger.error("Disbursement envelope error response constructed")
        return disbursement_envelope_response

    # noinspection PyMethodMayBeStatic
    async def validate_envelope_payload(
        self, disbursement_envelope_payload: DisbursementEnvelopePayload
    ) -> bool:
        _logger.info("Validating disbursement envelope payload")
        if (
            disbursement_envelope_payload.benefit_program_mnemonic is None
            or disbursement_envelope_payload.benefit_program_mnemonic == ""
        ):
            _logger.error("Invalid benefit program mnemonic")
            raise DisbursementEnvelopeException(
                G2PBridgeErrorCodes.INVALID_PROGRAM_MNEMONIC
            )
        if (
            disbursement_envelope_payload.disbursement_frequency
            not in DisbursementFrequency
        ):
            _logger.error("Invalid disbursement frequency")
            raise DisbursementEnvelopeException(
                G2PBridgeErrorCodes.INVALID_DISBURSEMENT_FREQUENCY
            )
        if (
            disbursement_envelope_payload.cycle_code_mnemonic is None
            or disbursement_envelope_payload.cycle_code_mnemonic == ""
        ):
            _logger.error("Invalid cycle code mnemonic")
            raise DisbursementEnvelopeException(
                G2PBridgeErrorCodes.INVALID_CYCLE_CODE_MNEMONIC
            )
        if (
            disbursement_envelope_payload.number_of_beneficiaries is None
            or disbursement_envelope_payload.number_of_beneficiaries < 1
        ):
            _logger.error("Invalid number of beneficiaries")
            raise DisbursementEnvelopeException(
                G2PBridgeErrorCodes.INVALID_NO_OF_BENEFICIARIES
            )
        if (
            disbursement_envelope_payload.number_of_disbursements is None
            or disbursement_envelope_payload.number_of_disbursements < 1
        ):
            _logger.error("Invalid number of disbursements")
            raise DisbursementEnvelopeException(
                G2PBridgeErrorCodes.INVALID_NO_OF_DISBURSEMENTS
            )
        if (
            disbursement_envelope_payload.total_disbursement_quantity is None
            or disbursement_envelope_payload.total_disbursement_quantity < 0
        ):
            _logger.error("Invalid total disbursed quantity")
            raise DisbursementEnvelopeException(
                G2PBridgeErrorCodes.INVALID_TOTAL_DISBURSED_QUANTITY
            )
        if (
            disbursement_envelope_payload.disbursement_schedule_date is None
            or disbursement_envelope_payload.disbursement_schedule_date
            < datetime.date(datetime.now())  # TODO: Add a delta of x days
        ):
            _logger.error("Invalid disbursement schedule date")
            raise DisbursementEnvelopeException(
                G2PBridgeErrorCodes.INVALID_DISBURSEMENT_SCHEDULE_DATE
            )
        _logger.info("Disbursement envelope payload validated!")
        return True

    # noinspection PyMethodMayBeStatic
    async def construct_disbursement_envelope(
        self, disbursement_envelope_payload: DisbursementEnvelopePayload
    ) -> DisbursementEnvelope:
        _logger.info("Constructing disbursement envelope")
        disbursement_envelope: DisbursementEnvelope = DisbursementEnvelope(
            disbursement_envelope_id=str(uuid.uuid4()),
            benefit_program_mnemonic=disbursement_envelope_payload.benefit_program_mnemonic,
            benefit_code=disbursement_envelope_payload.benefit_code,
            benefit_type=disbursement_envelope_payload.benefit_type,
            cash_distribution_mode=disbursement_envelope_payload.cash_distribution_mode,
            disbursement_cycle_id=disbursement_envelope_payload.disbursement_cycle_id,
            disbursement_frequency=disbursement_envelope_payload.disbursement_frequency,
            cycle_code_mnemonic=disbursement_envelope_payload.cycle_code_mnemonic,
            number_of_beneficiaries=disbursement_envelope_payload.number_of_beneficiaries,
            number_of_disbursements=disbursement_envelope_payload.number_of_disbursements,
            total_disbursement_quantity=disbursement_envelope_payload.total_disbursement_quantity,
            measurement_unit=disbursement_envelope_payload.measurement_unit,
            disbursement_schedule_date=disbursement_envelope_payload.disbursement_schedule_date,
            receipt_time_stamp=datetime.now(),
            cancellation_status=CancellationStatus.NOT_CANCELLED.value,
            cancellation_timestamp=None,
            active=True,
        )
        _logger.info("Disbursement envelope constructed successfully")
        return disbursement_envelope

    # noinspection PyMethodMayBeStatic
    async def construct_envelope_control(
        self, disbursement_envelope: DisbursementEnvelope
    ) -> EnvelopeControl:
        _logger.info("Constructing envelope control")
        return EnvelopeControl(
            disbursement_envelope_id=disbursement_envelope.disbursement_envelope_id,
            active=True,
        )

    # noinspection PyMethodMayBeStatic
    async def construct_envelope_batch_status_for_digital_cash(
        self, disbursement_envelope: DisbursementEnvelope, session
    ) -> EnvelopeBatchStatusForDigitalCash:
        _logger.info("Constructing envelope batch status for digital cash")
        benefit_program_configuration: BenefitProgramConfiguration = (
            (
                await session.execute(
                    select(BenefitProgramConfiguration).where(
                        BenefitProgramConfiguration.benefit_program_mnemonic
                        == disbursement_envelope.benefit_program_mnemonic
                    )
                )
            )
            .scalars()
            .first()
        )
        if benefit_program_configuration is None:
            _logger.error("Benefit program configuration not found")
            raise DisbursementEnvelopeException(
                G2PBridgeErrorCodes.INVALID_PROGRAM_MNEMONIC
            )

        return EnvelopeBatchStatusForDigitalCash(
            disbursement_envelope_id=disbursement_envelope.disbursement_envelope_id,
            funds_available_with_bank=FundsAvailableWithBankEnum.PENDING_CHECK.value,
            funds_blocked_with_bank=FundsBlockedWithBankEnum.PENDING_CHECK.value,
            active=True
        )

    async def validate_envelope_amend_request(
        self, disbursement_envelope_request: DisbursementEnvelopeRequest
    ) -> bool:
        _logger.info("Validating disbursement envelope amend request")
        disbursement_envelope_payload: DisbursementEnvelopePayload = (
            disbursement_envelope_request.message
        )
        if (
            disbursement_envelope_payload.disbursement_envelope_id is None
            or disbursement_envelope_payload.disbursement_envelope_id == ""
        ):
            _logger.error("Invalid disbursement envelope ID")
            raise DisbursementEnvelopeException(
                G2PBridgeErrorCodes.INVALID_DISBURSEMENT_ENVELOPE_ID
            )
        if (
            disbursement_envelope_payload.number_of_beneficiaries is None
            or disbursement_envelope_payload.number_of_beneficiaries < 1
        ):
            _logger.error("Invalid number of beneficiaries")
            raise DisbursementEnvelopeException(
                G2PBridgeErrorCodes.INVALID_NO_OF_BENEFICIARIES
            )
        if (
            disbursement_envelope_payload.number_of_disbursements is None
            or disbursement_envelope_payload.number_of_disbursements < 1
        ):
            _logger.error("Invalid number of disbursements")
            raise DisbursementEnvelopeException(
                G2PBridgeErrorCodes.INVALID_NO_OF_DISBURSEMENTS
            )
        if (
            disbursement_envelope_payload.total_disbursement_quantity is None
            or disbursement_envelope_payload.total_disbursement_quantity < 0
        ):
            _logger.error("Invalid total disbursed quantity")
            raise DisbursementEnvelopeException(
                G2PBridgeErrorCodes.INVALID_TOTAL_DISBURSED_QUANTITY
            )
        if (
            disbursement_envelope_payload.disbursement_schedule_date is None
            or disbursement_envelope_payload.disbursement_schedule_date
            < datetime.date(datetime.now())
        ):
            _logger.error("Invalid disbursement schedule date")
            raise DisbursementEnvelopeException(
                G2PBridgeErrorCodes.INVALID_DISBURSEMENT_SCHEDULE_DATE
            )
        return True

    async def update_disbursement_envelope(
        self, disbursement_envelope_payload: DisbursementEnvelopePayload, session
    ) -> DisbursementEnvelopePayload:
        _logger.info("Updating disbursement envelope")
        disbursement_envelope: DisbursementEnvelope = (
            await session.execute(
                select(DisbursementEnvelope).where(
                    DisbursementEnvelope.id == disbursement_envelope_payload.id
                )
            )
        ).scalar()

        disbursement_envelope.number_of_beneficiaries = (
            disbursement_envelope_payload.number_of_beneficiaries
        )
        disbursement_envelope.number_of_disbursements = (
            disbursement_envelope_payload.number_of_disbursements
        )
        disbursement_envelope.total_disbursement_quantity = (
            disbursement_envelope_payload.total_disbursement_quantity
        )
        disbursement_envelope.disbursement_schedule_date = (
            disbursement_envelope_payload.disbursement_schedule_date
        )

        await session.commit()
        _logger.info("Disbursement envelope updated successfully")
        return disbursement_envelope_payload

    async def amend_disbursement_envelope(
        self, disbursement_envelope_request: DisbursementEnvelopeRequest
    ) -> DisbursementEnvelopePayload:
        _logger.info("Amending disbursement envelope")
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            try:
                await self.validate_envelope_amend_request(
                    disbursement_envelope_request
                )
            except DisbursementEnvelopeException as e:
                raise e

            disbursement_envelope_payload: DisbursementEnvelopePayload = (
                disbursement_envelope_request.message
            )
            disbursement_envelope_id: str = (
                disbursement_envelope_payload.disbursement_envelope_id
            )

            result = await session.execute(
                select(DisbursementEnvelope)
                .where(
                    DisbursementEnvelope.disbursement_envelope_id
                    == disbursement_envelope_id
                )
                .with_for_update()
            )
            disbursement_envelope: DisbursementEnvelope = result.scalar_one_or_none()

            if disbursement_envelope is None:
                _logger.error(
                    f"Disbursement envelope with ID {disbursement_envelope_id} not found"
                )
                raise DisbursementEnvelopeException(
                    G2PBridgeErrorCodes.DISBURSEMENT_ENVELOPE_NOT_FOUND
                )

            if (
                disbursement_envelope.cancellation_status
                == CancellationStatus.CANCELLED.value
            ):
                _logger.error(
                    f"Disbursement envelope with ID {disbursement_envelope_id} already cancelled"
                )
                raise DisbursementEnvelopeException(
                    G2PBridgeErrorCodes.DISBURSEMENT_ENVELOPE_ALREADY_CANCELED
                )

            if disbursement_envelope.disbursement_schedule_date <= datetime.date(
                datetime.now()
            ):
                _logger.error(
                    f"Disbursement envelope with ID {disbursement_envelope_id} date is already passed"
                )
                raise DisbursementEnvelopeException(
                    G2PBridgeErrorCodes.DISBURSEMENT_ENVELOPE_DATE_PASSED
                )

            disbursement_envelope_payload.disbursement_envelope_id = (
                disbursement_envelope_id
            )
            disbursement_envelope_payload.id = disbursement_envelope.id

            disbursement_envelope_payload = await self.update_disbursement_envelope(
                disbursement_envelope_payload, session
            )

            await session.commit()
            _logger.info("Disbursement envelope amended successfully")
            return disbursement_envelope_payload
