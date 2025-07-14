import asyncio
import datetime
import logging
import uuid
from typing import Optional

from openg2p_g2p_bridge_models.models import (
    DisbursementBatchControlGeo,
    DisbursementEnvelope,
    DisbursementBatchControlGeoAttributes,
    NotificationLog,
    ProcessStatus,
)
from openg2p_g2p_bridge_models.schemas import (
    NotificationRequest,
    WarehouseNotificationPayload,
)
from openg2p_g2p_bridge_notification_connectors.models import (
    NotificationType, NotificationResponse, NotificationResponseStatus
)
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from ..app import celery_app, get_engine
from ..config import Settings
from ..helpers.notification_helper import NotificationHelper
from openg2p_g2p_bridge_notification_connectors.factory import NotificationFactory
from openg2p_g2p_bridge_notification_connectors.models import Recipient

_config = Settings.get_config()
_engine = get_engine()
NOTIFICATION_SERVICE_URL = _config.notification_service_url

_logger = logging.getLogger("warehouse_notification_worker")


@celery_app.task(name="warehouse_notification_worker")
def warehouse_notification_worker(disbursement_batch_control_geo_id: str) -> None:
    session_maker = sessionmaker(
        bind=_engine.get("db_engine_bridge"), expire_on_commit=False
    )
    with session_maker() as session:
        disbursement_batch_control_geo: Optional[DisbursementBatchControlGeo] = None
        try:
            # Fetch the batch control geo record
            disbursement_batch_control_geo = (
                (
                    session.execute(
                        select(DisbursementBatchControlGeo).where(
                            DisbursementBatchControlGeo.id
                            == disbursement_batch_control_geo_id
                        )
                    )
                )
                .scalars()
                .first()
            )
            if not disbursement_batch_control_geo:
                _logger.error(
                    f"No batch control geo found for id {disbursement_batch_control_geo_id}"
                )
                return

            # Fetch the related DisbursementEnvelope
            disbursement_envelope = (
                (
                    session.execute(
                        select(DisbursementEnvelope).where(
                            DisbursementEnvelope.id
                            == disbursement_batch_control_geo.disbursement_envelope_id
                        )
                    )
                )
                .scalars()
                .first()
            )
            if not disbursement_envelope:
                _logger.error(
                    f"No DisbursementEnvelope found for id {disbursement_batch_control_geo.disbursement_envelope_id}"
                )
                return

            # Build notification payload
            notification_payload = WarehouseNotificationPayload(
                program_mnemonic=getattr(
                    disbursement_envelope, "benefit_program_mnemonic", None
                ),
                program_description=None,
                target_registry=getattr(disbursement_envelope, "target_registry", None),
                disbursement_cycle_mnemonic=getattr(
                    disbursement_batch_control_geo, "disbursement_cycle_id", None
                ),
                disbursement_date=str(
                    getattr(disbursement_envelope, "disbursement_schedule_date", None)
                ),
                benefit_code_id=getattr(disbursement_envelope, "benefit_code_id", None),
                benefit_code_mnemonic=getattr(
                    disbursement_envelope, "benefit_code_mnemonic", None
                ),
                benefit_type=getattr(disbursement_envelope, "benefit_type", None),
                measurement_unit=getattr(
                    disbursement_envelope, "measurement_unit", None
                ),
                benefit_description=None,
                warehouse_id=getattr(
                    disbursement_batch_control_geo, "warehouse_id", None
                ),
                warehouse_mnemonic=getattr(
                    disbursement_batch_control_geo, "warehouse_mnemonic", None
                ),
                agency_id=getattr(disbursement_batch_control_geo, "agency_id", None),
                agency_mnemonic=getattr(
                    disbursement_batch_control_geo, "agency_mnemonic", None
                ),
                agency_description=None,
                total_quantity=getattr(
                    disbursement_batch_control_geo, "total_quantity", None
                ),
                no_of_bebeficiaries=getattr(
                    disbursement_batch_control_geo, "no_of_beneficiaries", None
                ),
                administrative_zone_id_large=getattr(
                    disbursement_batch_control_geo, "administrative_zone_id_large", None
                ),
                administrative_zone_mnemonic_large=getattr(
                    disbursement_batch_control_geo,
                    "administrative_zone_mnemonic_large",
                    None,
                ),
                administrative_zone_id_small=getattr(
                    disbursement_batch_control_geo, "administrative_zone_id_small", None
                ),
                administrative_zone_mnemonic_small=getattr(
                    disbursement_batch_control_geo,
                    "administrative_zone_mnemonic_small",
                    None,
                ),
            )
            # Generate notification_id
            notification_id = str(uuid.uuid4())
            # Create NotificationLog entry (PENDING)
            notification_log = NotificationLog(
                id=notification_id,
                notification_type=NotificationType.WAREHOUSE_NOTIFICATION.value,
                recipient=disbursement_batch_control_geo.warehouse_mnemonic,
                payload=str(notification_payload.model_dump()),
                sent_at=datetime.datetime.now(),
            )
            session.add(notification_log)
            session.commit()

            disbursement_batch_control_geo_attributes = (
                session.execute(
                    select(DisbursementBatchControlGeoAttributes).where(
                        DisbursementBatchControlGeoAttributes.id
                        == disbursement_batch_control_geo.id
                    )
                )
                .scalars()
                .first()
            )
            if not disbursement_batch_control_geo_attributes:
                _logger.error(
                    f"No DisbursementBatchControlGeoAttributes found for id {disbursement_batch_control_geo.id}"
                )
                return
                

            # Send notification 
            notifier = NotificationFactory.get_notifier()
            recipient = Recipient(
                recipient_id=disbursement_batch_control_geo_attributes.warehouse_id,
                recipient_name=disbursement_batch_control_geo_attributes.warehouse_admin_name,
                recipient_email=disbursement_batch_control_geo_attributes.warehouse_admin_email,
                recipient_phone=disbursement_batch_control_geo_attributes.warehouse_admin_phone
            )
            try:
                notification_response: NotificationResponse = notifier.send_notification(
                    notification_id=notification_id,
                    payload=notification_payload.model_dump(),
                    notification_type=NotificationType.WAREHOUSE_NOTIFICATION.value,
                    recipient=recipient
                )
                if notification_response.status == NotificationResponseStatus.FAILURE:
                    raise Exception(notification_response.error_message or "Notification failed")
                
                notification_log.status = notification_response.status.value
                notification_log.response = notification_response.response if notification_response else "SENT"
                notification_log.processed_at = datetime.datetime.now()
                disbursement_batch_control_geo.warehouse_notification_status = (
                    ProcessStatus.PROCESSED.value
                )
            except Exception as e:
                notification_log.status = "ERROR"
                notification_log.error_message = str(e)
                notification_log.processed_at = datetime.datetime.now()
                _logger.error(f"Warehouse notification failed: {e}")
                raise e
            session.commit()

        except Exception as e:
            session.rollback()
            _logger.error(f"Warehouse notification failed: {e}")
            if disbursement_batch_control_geo:
                disbursement_batch_control_geo.warehouse_notification_attempts += 1
                disbursement_batch_control_geo.warehouse_notification_latest_error_code = str(e)
                disbursement_batch_control_geo.warehouse_notification_status = (
                    ProcessStatus.PENDING.value
                )
            if disbursement_batch_control_geo.warehouse_notification_attempts > _config.warehouse_notification_max_attempts:
                disbursement_batch_control_geo.warehouse_notification_status = (
                    ProcessStatus.ERROR.value
                )
            session.commit()
