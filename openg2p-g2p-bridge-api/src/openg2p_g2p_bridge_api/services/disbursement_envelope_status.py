import logging
from datetime import datetime

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService
from openg2p_g2p_bridge_models.errors.codes import G2PBridgeErrorCodes
from openg2p_g2p_bridge_models.errors.exceptions import DisbursementStatusException
from openg2p_g2p_bridge_models.models import (
    BenefitType,
    DisbursementBatchControlGeo,
    DisbursementEnvelope,
    DisbursementResolutionGeoAddress,
    EnvelopeBatchStatusForDigitalCash,
    EnvelopeControl,
    ProcessStatus,
)
from openg2p_g2p_bridge_models.schemas import (
    DisbursementEnvelopeBatchStatusPayload,
    DisbursementEnvelopeStatusRequest,
    DisbursementEnvelopeStatusResponse,
    DistributionDetailsForEnvelope,
    EnvelopeStatusForDigitalCashPayload,
    EnvelopeStatusForPhysicalBenefitsPayload,
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
            envelope = (
                (
                    await session.execute(
                        select(DisbursementEnvelope).where(
                            DisbursementEnvelope.disbursement_envelope_id
                            == disbursement_envelope_status_request.message
                        )
                    )
                )
                .scalars()
                .first()
            )
            if not envelope:
                raise DisbursementStatusException(
                    code=G2PBridgeErrorCodes.DISBURSEMENT_ENVELOPE_NOT_FOUND,
                    message="Disbursement envelope not found",
                )

            envelope_control = (
                (
                    await session.execute(
                        select(EnvelopeControl).where(
                            EnvelopeControl.disbursement_envelope_id
                            == envelope.disbursement_envelope_id
                        )
                    )
                )
                .scalars()
                .first()
            )

            # Fetch batch_control_geos for physical, digital_cash_status for digital
            batch_control_geos = None
            envelope_batch_status_for_digital_cash = None
            beneficiary_notified_count = None
            disbursement_details = None
            if envelope.benefit_type == BenefitType.CASH_DIGITAL:
                envelope_batch_status_for_digital_cash = (
                    (
                        await session.execute(
                            select(EnvelopeBatchStatusForDigitalCash).where(
                                EnvelopeBatchStatusForDigitalCash.disbursement_envelope_id
                                == envelope.disbursement_envelope_id
                            )
                        )
                    )
                    .scalars()
                    .first()
                )
            else:
                batch_control_geos = (
                    (
                        await session.execute(
                            select(DisbursementBatchControlGeo).where(
                                DisbursementBatchControlGeo.disbursement_envelope_id
                                == envelope.disbursement_envelope_id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                disbursement_details = [
                    DistributionDetailsForEnvelope(
                        administrative_zone_id_large=batch_control_geo.administrative_zone_id_large,
                        administrative_zone_mnemonic_large=batch_control_geo.administrative_zone_mnemonic_large,
                        administrative_zone_id_small=batch_control_geo.administrative_zone_id_small,
                        administrative_zone_mnemonic_small=batch_control_geo.administrative_zone_mnemonic_small,
                        warehouse_id=batch_control_geo.warehouse_id,
                        warehouse_mnemonic=batch_control_geo.warehouse_mnemonic,
                        agency_id=batch_control_geo.agency_id,
                        agency_mnemonic=batch_control_geo.agency_mnemonic,
                        number_of_beneficiaries=batch_control_geo.no_of_beneficiaries,
                        total_disbursement_quantity=batch_control_geo.total_quantity,
                        warehouse_notified=batch_control_geo.warehouse_notification_status
                        == ProcessStatus.PROCESSED,
                        agency_notified=batch_control_geo.agency_notification_status
                        == ProcessStatus.PROCESSED,
                        no_of_pods_received=None,  # Fill if available
                    )
                    for batch_control_geo in batch_control_geos
                ]
                beneficiary_notified_count = (
                    (
                        await session.execute(
                            select(DisbursementResolutionGeoAddress).where(
                                DisbursementResolutionGeoAddress.disbursement_envelope_id
                                == envelope.disbursement_envelope_id,
                                DisbursementResolutionGeoAddress.beneficiary_notification_status
                                == ProcessStatus.PROCESSED,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

            return await self.construct_batch_status_payload(
                envelope=envelope,
                envelope_control=envelope_control,
                batch_control_geos=batch_control_geos,
                digital_cash_status=envelope_batch_status_for_digital_cash,
                beneficiary_notified_count=beneficiary_notified_count,
                disbursement_details=disbursement_details,
            )

    async def construct_batch_status_payload(
        self,
        envelope: DisbursementEnvelope,
        envelope_control: EnvelopeControl,
        batch_control_geos=None,
        digital_cash_status=None,
        beneficiary_notified_count=None,
        disbursement_details=None,
    ):
        # DIGITAL CASH
        if digital_cash_status:
            return EnvelopeStatusForDigitalCashPayload(
                disbursement_envelope_id=envelope.disbursement_envelope_id,
                benefit_code_id=envelope.benefit_code_id,
                benefit_code_mnemonic=envelope.benefit_code_mnemonic,
                benefit_type=envelope.benefit_type.value,
                number_of_disbursements_declared=envelope.number_of_disbursements,
                number_of_disbursements_received=envelope_control.number_of_disbursements_received
                if envelope_control
                else 0,
                total_disbursement_quantity_declared=envelope.total_disbursement_quantity,
                total_disbursement_quantity_received=envelope_control.total_disbursement_quantity_received
                if envelope_control
                else 0,
                funds_available_with_bank=digital_cash_status.funds_available_with_bank
                if digital_cash_status
                else None,
                funds_available_latest_timestamp=digital_cash_status.funds_available_latest_timestamp
                if digital_cash_status
                else None,
                funds_available_latest_error_code=digital_cash_status.funds_available_latest_error_code
                if digital_cash_status
                else None,
                funds_available_attempts=digital_cash_status.funds_available_attempts
                if digital_cash_status
                else 0,
                funds_blocked_with_bank=digital_cash_status.funds_blocked_with_bank
                if digital_cash_status
                else None,
                funds_blocked_latest_timestamp=digital_cash_status.funds_blocked_latest_timestamp
                if digital_cash_status
                else None,
                funds_blocked_latest_error_code=digital_cash_status.funds_blocked_latest_error_code
                if digital_cash_status
                else None,
                funds_blocked_attempts=digital_cash_status.funds_blocked_attempts
                if digital_cash_status
                else 0,
                funds_blocked_reference_number=digital_cash_status.funds_blocked_reference_number
                if digital_cash_status
                else None,
                id_mapper_resolution_required=None,  # Fill if available
                number_of_disbursements_shipped=digital_cash_status.number_of_disbursements_shipped
                if digital_cash_status
                else 0,
                number_of_disbursements_reconciled=digital_cash_status.number_of_disbursements_reconciled
                if digital_cash_status
                else 0,
                number_of_disbursements_reversed=digital_cash_status.number_of_disbursements_reversed
                if digital_cash_status
                else 0,
            )
        # PHYSICAL BENEFITS
        else:
            warehouse_ids = (
                {geo.warehouse_id for geo in batch_control_geos if geo.warehouse_id}
                if batch_control_geos
                else set()
            )
            agency_ids = (
                {geo.agency_id for geo in batch_control_geos if geo.agency_id}
                if batch_control_geos
                else set()
            )
            warehouses_notified = (
                {
                    geo.warehouse_id
                    for geo in batch_control_geos
                    if geo.warehouse_id
                    and geo.warehouse_notification_status == ProcessStatus.PROCESSED
                }
                if batch_control_geos
                else set()
            )
            agencies_notified = (
                {
                    geo.agency_id
                    for geo in batch_control_geos
                    if geo.agency_id
                    and geo.agency_notification_status == ProcessStatus.PROCESSED
                }
                if batch_control_geos
                else set()
            )
            return EnvelopeStatusForPhysicalBenefitsPayload(
                disbursement_envelope_id=envelope.disbursement_envelope_id,
                benefit_code_id=envelope.benefit_code_id,
                benefit_code_mnemonic=envelope.benefit_code_mnemonic,
                benefit_type=envelope.benefit_type.value,
                number_of_beneficiaries_received=envelope.number_of_beneficiaries,
                number_of_beneficiaries_declared=envelope.number_of_beneficiaries,
                number_of_disbursements_declared=envelope.number_of_disbursements,
                number_of_disbursements_received=envelope_control.number_of_disbursements_received
                if envelope_control
                else 0,
                total_disbursement_quantity_declared=envelope.total_disbursement_quantity,
                total_disbursement_quantity_received=envelope_control.total_disbursement_quantity_received
                if envelope_control
                else 0,
                disbursement_details_for_envelope=disbursement_details,
                no_of_warehouses_allocated=len(warehouse_ids) if warehouse_ids else 0,
                no_of_warehouses_notified=len(warehouses_notified)
                if warehouses_notified
                else 0,
                no_of_agencies_allocated=len(agency_ids) if agency_ids else 0,
                no_of_agencies_notified=len(agencies_notified)
                if agencies_notified
                else 0,
                no_of_beneficiaries_notified=len(beneficiary_notified_count)
                if beneficiary_notified_count is not None
                else 0,
                no_of_pods_received=None,  # Fill if available
            )

    async def construct_disbursement_envelope_status_error_response(
        self,
        disbursement_envelope_status_request: DisbursementEnvelopeStatusRequest,
        code: str,
    ) -> DisbursementEnvelopeStatusResponse:
        response = DisbursementEnvelopeStatusResponse(
            header=SyncResponseHeader(
                message_id=disbursement_envelope_status_request.header.message_id,
                message_ts=datetime.now().isoformat(),
                action=disbursement_envelope_status_request.header.action,
                status=StatusEnum.rjct,
                status_reason_message=code,
            ),
            message=None,
        )
        return response

    async def construct_disbursement_envelope_status_success_response(
        self,
        disbursement_envelope_status_request: DisbursementEnvelopeStatusRequest,
        disbursement_envelope_batch_status_payload: EnvelopeStatusForDigitalCashPayload
        | EnvelopeStatusForPhysicalBenefitsPayload,
    ) -> DisbursementEnvelopeStatusResponse:
        """
        Returns a DisbursementEnvelopeStatusResponse with the correct payload type (digital or physical).
        """
        response = DisbursementEnvelopeStatusResponse(
            header=SyncResponseHeader(
                message_id=disbursement_envelope_status_request.header.message_id,
                message_ts=datetime.now().isoformat(),
                action=disbursement_envelope_status_request.header.action,
                status=StatusEnum.succ,
            ),
            message=disbursement_envelope_batch_status_payload,
        )
        return response
