import logging
import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from openg2p_g2p_bridge_models.models import (
    DisbursementBatchControlGeo,
    ProcessStatus,
)

from ..app import celery_app, get_engine
from ..config import Settings
import httpx

_config = Settings.get_config()
_engine = get_engine()
NOTIFICATION_SERVICE_URL = _config.notification_service_url

_logger = logging.getLogger("warehouse_notification_worker")

@celery_app.task(name="warehouse_notification_worker")
def warehouse_notification_worker(disbursement_control_geo_id: str) -> None:
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
                "disbursement_batch_control_geo_id": getattr(disbursement_batch_control_geo, "disbursement_batch_control_geo", None),
                "program_mnemonic": getattr(disbursement_batch_control_geo, "program_mnemonic", None),
                "program_description": getattr(disbursement_batch_control_geo, "program_mnemonic", None),
                "benefit_code_id": getattr(disbursement_batch_control_geo, "benefit_code_id", None),
                "benefit_type": getattr(disbursement_batch_control_geo, "benefit_type", None),
                "benefit_description": getattr(disbursement_batch_control_geo, "benefit_code_id", None),
                "disbursement_cycle_mnemonic": getattr(disbursement_batch_control_geo, "disbursement_cycle_mnemonic", None),
                "disbursement_quantity": getattr(disbursement_batch_control_geo, "total_quantity", None),
                "no_of_bebeficiaries": getattr(disbursement_batch_control_geo, "no_of_bebeficiaries", None),
                "disbursement_date": str(getattr(disbursement_batch_control_geo, "disbursement_date", None)),
                "agency_mnemonic": getattr(disbursement_batch_control_geo, "agency_mnemonic", None),
            }
            # Prepare notification request
            notification_request = {
                "notification_request_id": str(uuid.uuid4()),
                "recipient": disbursement_batch_control_geo.warehouse_mnemonic,
                "recipient_type": "WAREHOUSE",
                "event": "WAREHOUSE_NOTIFICATION",
                "notification_payload": notification_payload,
            }
            # TODO: Persist this into NotificationLog with disbursement_batch_control_geo_id
            # Send to notification microservice
            # with httpx.AsyncClient() as client:
            #     response = client.post(NOTIFICATION_SERVICE_URL, json=notification_request)
            #     response.raise_for_status()
            # Update status to PROCESSED
            disbursement_batch_control_geo.warehouse_notification_status = ProcessStatus.PROCESSED
            session.commit()
        except Exception as e:
            _logger.error(f"Warehouse notification failed: {e}")
            if disbursement_batch_control_geo:
                disbursement_batch_control_geo.warehouse_notification_status = ProcessStatus.ERROR
                session.commit() 