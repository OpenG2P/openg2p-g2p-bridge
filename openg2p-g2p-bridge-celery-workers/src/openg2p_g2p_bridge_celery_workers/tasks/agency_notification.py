import logging
from typing import Optional, Dict, Any
from openg2p_fastapi_common.context import dbengine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select
from openg2p_g2p_bridge_models.models import (
    DisbursementBatchControlGeo,
    ProcessStatus,
)
from openg2p_g2p_bridge_celery_workers.app import celery_app
from ..config import Settings
import httpx

_config = Settings.get_config()
NOTIFICATION_SERVICE_URL = _config.notification_service_url

_logger = logging.getLogger("agency_notification_worker")

@celery_app.task(name="agency_notification_worker")
async def agency_notification_worker(disbursement_control_geo_id: str) -> None:
    session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
    async with session_maker() as session:
        disbursement_batch_control_geo: Optional[DisbursementBatchControlGeo] = None
        try:
            # Fetch the batch control geo record
            disbursement_batch_control_geo = (
                await session.execute(
                    select(DisbursementBatchControlGeo).where(
                        DisbursementBatchControlGeo.disbursement_control_geo_id == disbursement_control_geo_id
                    )
                )
            ).scalars().first()
            if not disbursement_batch_control_geo:
                _logger.error(f"No batch control geo found for id {disbursement_control_geo_id}")
                return
            # Build notification payload
            notification_payload: Dict[str, Any] = {
                "disbursement_id": getattr(disbursement_batch_control_geo, "disbursement_id", None),
                "program_mnemonic": getattr(disbursement_batch_control_geo, "program_mnemonic", None),
                "program_description": getattr(disbursement_batch_control_geo, "program_description", None),
                "benefit_code": getattr(disbursement_batch_control_geo, "benefit_code", None),
                "benefit_type": getattr(disbursement_batch_control_geo, "benefit_type", None),
                "benefit_description": getattr(disbursement_batch_control_geo, "benefit_description", None),
                "disbursement_cycle_mnemonic": getattr(disbursement_batch_control_geo, "disbursement_cycle_mnemonic", None),
                "disbursement_quantity": getattr(disbursement_batch_control_geo, "total_quantity", None),
                "disbursement_date": str(getattr(disbursement_batch_control_geo, "disbursement_date", None)),
                "agency_mnemonic": getattr(disbursement_batch_control_geo, "agency_mnemonic", None),
            }
            # Prepare notification request
            notification_request = {
                "disbursement_control_geo_id": disbursement_batch_control_geo.disbursement_control_geo_id,
                "agency_mnemonic": disbursement_batch_control_geo.agency_mnemonic,
                "recipient_type": "AGENCY",
                "event": "AGENCY_NOTIFICATION",
                "notification_payload": notification_payload,
            }
            # Send to notification microservice
            async with httpx.AsyncClient() as client:
                response = await client.post(NOTIFICATION_SERVICE_URL, json=notification_request)
                response.raise_for_status()
            # Update status to PROCESSED
            disbursement_batch_control_geo.agency_notification_status = ProcessStatus.PROCESSED
            await session.commit()
        except Exception as e:
            _logger.error(f"Agency notification failed: {e}")
            if disbursement_batch_control_geo:
                disbursement_batch_control_geo.agency_notification_status = ProcessStatus.ERROR
                await session.commit() 