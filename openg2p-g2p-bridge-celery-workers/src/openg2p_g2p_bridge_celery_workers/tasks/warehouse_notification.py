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

_logger = logging.getLogger("warehouse_notification_worker")

@celery_app.task(name="warehouse_notification_worker")
async def warehouse_notification_worker(disbursement_control_geo_id: str) -> None:
    session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
    async with session_maker() as session:
        geo: Optional[DisbursementBatchControlGeo] = None
        try:
            # Fetch the batch control geo record
            geo = (
                await session.execute(
                    select(DisbursementBatchControlGeo).where(
                        DisbursementBatchControlGeo.disbursement_control_geo_id == disbursement_control_geo_id
                    )
                )
            ).scalars().first()
            if not geo:
                _logger.error(f"No batch control geo found for id {disbursement_control_geo_id}")
                return
            # Build notification payload
            notification_payload: Dict[str, Any] = {
                "disbursement_id": getattr(geo, "disbursement_id", None),
                "program_mnemonic": getattr(geo, "program_mnemonic", None),
                "program_description": getattr(geo, "program_description", None),
                "benefit_code": getattr(geo, "benefit_code", None),
                "benefit_type": getattr(geo, "benefit_type", None),
                "benefit_description": getattr(geo, "benefit_description", None),
                "disbursement_cycle_mnemonic": getattr(geo, "disbursement_cycle_mnemonic", None),
                "disbursement_quantity": getattr(geo, "total_quantity", None),
                "disbursement_date": str(getattr(geo, "disbursement_date", None)),
                "agency_mnemonic": getattr(geo, "agency_mnemonic", None),
            }
            # Prepare notification request
            notification_request = {
                "disbursement_control_geo_id": geo.disbursement_control_geo_id,
                "warehouse_mnemonic": geo.warehouse_mnemonic,
                "recipient_type": "WAREHOUSE",
                "event": "WAREHOUSE_NOTIFICATION",
                "notification_payload": notification_payload,
            }
            # Send to notification microservice
            async with httpx.AsyncClient() as client:
                response = await client.post(NOTIFICATION_SERVICE_URL, json=notification_request)
                response.raise_for_status()
            # Update status to PROCESSED
            geo.warehouse_notification_status = ProcessStatus.PROCESSED
            await session.commit()
        except Exception as e:
            _logger.error(f"Warehouse notification failed: {e}")
            if geo:
                geo.warehouse_notification_status = ProcessStatus.ERROR
                await session.commit() 