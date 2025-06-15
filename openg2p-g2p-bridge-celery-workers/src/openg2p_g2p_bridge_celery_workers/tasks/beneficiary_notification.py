import logging
from typing import Optional, Dict, Any
from openg2p_fastapi_common.context import dbengine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select
from openg2p_g2p_bridge_models.models import (
    DisbursementResolutionGeoAddress,
    ProcessStatus,
    DisbursementEnvelope,
)
from openg2p_g2p_bridge_celery_workers.app import celery_app
import httpx
from ..config import Settings

_logger = logging.getLogger("beneficiary_notification_worker")
_config = Settings.get_config()

NOTIFICATION_SERVICE_URL = _config.notification_service_url


@celery_app.task(name="beneficiary_notification_worker")
async def beneficiary_notification_worker(disbursement_id: str) -> None:
    session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
    async with session_maker() as session:
        try:
            # Fetch the geo address record
            geo_address: Optional[DisbursementResolutionGeoAddress] = (
                await session.execute(
                    select(DisbursementResolutionGeoAddress).where(
                        DisbursementResolutionGeoAddress.disbursement_id == disbursement_id
                    )
                )
            ).scalars().first()
            if not geo_address:
                _logger.error(f"No geo address found for disbursement_id {disbursement_id}")
                return
            # Fetch the envelope for payload details
            envelope: Optional[DisbursementEnvelope] = (
                await session.execute(
                    select(DisbursementEnvelope).where(
                        DisbursementEnvelope.disbursement_envelope_id == geo_address.disbursement_envelope_id
                    )
                )
            ).scalars().first()
            if not envelope:
                _logger.error(f"No envelope found for id {geo_address.disbursement_envelope_id}")
                return
            # Build notification payload
            notification_payload: Dict[str, Any] = {
                "disbursement_id": geo_address.disbursement_id,
                "program_mnemonic": envelope.benefit_program_mnemonic,
                "benefit_code": envelope.benefit_code,
                "benefit_type": envelope.benefit_type.value if hasattr(envelope.benefit_type, 'value') else str(envelope.benefit_type),
                "disbursement_cycle_mnemonic": envelope.cycle_code_mnemonic,
                "disbursement_quantity": envelope.total_disbursement_quantity,
                "disbursement_date": str(envelope.disbursement_schedule_date),
            }
            # Prepare notification request
            notification_request = {
                "disbursement_id": geo_address.disbursement_id,
                "beneficiary_id": geo_address.beneficiary_id,
                "recipient_type": "BENEFICIARY",
                "event": "BENEFICIARY_NOTIFICATION",
                "notification_payload": notification_payload,
            }
            # Send to notification microservice
            async with httpx.AsyncClient() as client:
                response = await client.post(NOTIFICATION_SERVICE_URL, json=notification_request)
                response.raise_for_status()
            # Update status to PROCESSED
            geo_address.beneficiary_notification_status = ProcessStatus.PROCESSED
            await session.commit()
        except Exception as e:
            _logger.error(f"Beneficiary notification failed: {e}")
            if geo_address:
                geo_address.beneficiary_notification_status = ProcessStatus.ERROR
                await session.commit() 