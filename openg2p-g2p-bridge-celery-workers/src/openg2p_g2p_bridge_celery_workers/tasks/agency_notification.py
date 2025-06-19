import logging
from typing import Optional, Dict, Any
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
import asyncio

from openg2p_g2p_bridge_models.models import (
    DisbursementBatchControlGeo,
    ProcessStatus,
)
from ..config import Settings
from ..app import get_engine, celery_app
from ..helpers.notification_helper import NotificationHelper

_config = Settings.get_config()
_engine = get_engine()

NOTIFICATION_SERVICE_URL = _config.notification_service_url

_logger = logging.getLogger("agency_notification_worker")

@celery_app.task(name="agency_notification_worker")
def agency_notification_worker(disbursement_control_geo_id: str) -> None:
    session_maker = sessionmaker(bind=_engine, expire_on_commit=False)
    with session_maker() as session:
        disbursement_batch_control_geo: Optional[DisbursementBatchControlGeo] = None
        try:
            # Fetch the batch control geo record
            disbursement_batch_control_geo = (
                session.execute(
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
                "benefit_code_id": getattr(disbursement_batch_control_geo, "benefit_code_id", None),
                "benefit_type": getattr(disbursement_batch_control_geo, "benefit_type", None),
                "benefit_description": getattr(disbursement_batch_control_geo, "benefit_description", None),
                "disbursement_cycle_mnemonic": getattr(disbursement_batch_control_geo, "disbursement_cycle_mnemonic", None),
                "disbursement_quantity": getattr(disbursement_batch_control_geo, "total_quantity", None),
                "disbursement_date": str(getattr(disbursement_batch_control_geo, "disbursement_date", None)),
                "agency_mnemonic": getattr(disbursement_batch_control_geo, "agency_mnemonic", None),
                "warehouse_mnemonic": getattr(disbursement_batch_control_geo, "warehouse_mnemonic", None),
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
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            helper = NotificationHelper()
            loop.run_until_complete(helper.send_notification(NOTIFICATION_SERVICE_URL, notification_request))
            # Update status to PROCESSED
            disbursement_batch_control_geo.agency_notification_status = ProcessStatus.PROCESSED
            session.commit()
        except Exception as e:
            _logger.error(f"Agency notification failed: {e}")
            if disbursement_batch_control_geo:
                disbursement_batch_control_geo.agency_notification_status = ProcessStatus.ERROR
                session.commit() 