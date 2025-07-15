import datetime
import logging
import uuid
from typing import Optional

from openg2p_g2p_bridge_models.models import (
    Disbursement,
    DisbursementEnvelope,
    DisbursementResolutionGeoAddress,
    NotificationLog,
    ProcessStatus,
)
from openg2p_g2p_bridge_models.schemas import (
    BeneficiaryEntitlement,
    BeneficiaryNotificationPayload,
    NotificationRequest,
)
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from ..app import celery_app, get_engine
from ..config import Settings

from openg2p_g2p_bridge_notification_connectors.factory import NotificationFactory
from openg2p_g2p_bridge_notification_connectors.models import Recipient, NotificationResponse, NotificationType, NotificationResponseStatus

_logger = logging.getLogger("beneficiary_notification_worker")
_config = Settings.get_config()
_engine = get_engine()


@celery_app.task(name="beneficiary_notification_worker")
def beneficiary_notification_worker(disbursement_id: str) -> None:
    session_maker = sessionmaker(
        bind=_engine.get("db_engine_bridge"), expire_on_commit=False
    )
    with session_maker() as session:
        try:
            # Fetch the geo address record
            disbursement_resolution_geo_address: Optional[DisbursementResolutionGeoAddress] = (
                (
                    session.execute(
                        select(DisbursementResolutionGeoAddress).where(
                            DisbursementResolutionGeoAddress.disbursement_id
                            == disbursement_id
                        )
                    )
                )
                .scalars()
                .first()
            )
            if not disbursement_resolution_geo_address:
                _logger.error(
                    f"No geo address found for disbursement_id {disbursement_id}"
                )
                return
            # Fetch the envelope for payload details
            disbursement_envelope: Optional[DisbursementEnvelope] = (
                (
                    session.execute(
                        select(DisbursementEnvelope).where(
                            DisbursementEnvelope.id
                            == disbursement_resolution_geo_address.disbursement_envelope_id
                        )
                    )
                )
                .scalars()
                .first()
            )
            if not disbursement_envelope:
                _logger.error(
                    f"No envelope found for id {disbursement_resolution_geo_address.disbursement_envelope_id}"
                )
                return
            # Fetch the Disbursement for beneficiary_name and disbursement_quantity
            disbursement: Optional[Disbursement] = (
                (
                    session.execute(
                        select(Disbursement).where(
                            Disbursement.id == disbursement_id
                        )
                    )
                )
                .scalars()
                .first()
            )

            # Build notification payload
            notification_payload = construct_beneficiary_notification_payload(disbursement_resolution_geo_address, disbursement_envelope, disbursement)
            # Generate notification_id
            notification_id = str(uuid.uuid4())

            # Send to notification microservice
            notifier = NotificationFactory.get_component().get_notifier()
            recipient = Recipient(
                recipient_id=disbursement_resolution_geo_address.beneficiary_id,
                recipient_name=disbursement_resolution_geo_address.beneficiary_name,
                recipient_email=disbursement_resolution_geo_address.beneficiary_email,
                recipient_phone=disbursement_resolution_geo_address.beneficiary_phone,
            )
            notification_response: NotificationResponse = notifier.send_notification(
                notification_id=notification_id,
                payload=notification_payload.model_dump(),
                notification_type=NotificationType.BENEFICIARY_NOTIFICATION.value,
                recipient=recipient
            )

            # Create NotificationLog entry (PENDING)
            notification_log = NotificationLog(
                id=notification_id,
                notification_type=NotificationType.BENEFICIARY_NOTIFICATION.value,
                recipient=disbursement_resolution_geo_address.beneficiary_id,
                payload=str(notification_payload.model_dump()),
                sent_at=datetime.datetime.now(),
            )
            if notification_response.status == NotificationResponseStatus.FAILURE:
                raise Exception(notification_response.error_message or "Notification failed")
                
            notification_log.response = notification_response.response
            notification_log.processed_at = datetime.datetime.now()
            disbursement_resolution_geo_address.beneficiary_notification_status = ProcessStatus.PROCESSED.value

            session.add(notification_log)
            session.commit()

        except Exception as e:
            session.rollback()
            _logger.error(f"Warehouse notification failed: {e}")
            
            if notification_log:
                notification_log.response = notification_response.response
                notification_log.error_message = str(e)
                notification_log.processed_at = datetime.datetime.now()

            if disbursement_resolution_geo_address:
                disbursement_resolution_geo_address.beneficiary_notification_attempts += 1
                disbursement_resolution_geo_address.beneficiary_notification_latest_error_code = str(e)
                disbursement_resolution_geo_address.beneficiary_notification_status = ProcessStatus.PENDING.value

            if disbursement_resolution_geo_address.beneficiary_notification_attempts >= _config.beneficiary_notification_max_attempts:
                disbursement_resolution_geo_address.beneficiary_notification_status = ProcessStatus.ERROR.value
                session.commit()

def construct_beneficiary_notification_payload(disbursement_resolution_geo_address, disbursement_envelope, disbursement):
    notification_payload = BeneficiaryNotificationPayload(
        beneficiary_id=disbursement_resolution_geo_address.beneficiary_id,
        beneficiary_name=getattr(disbursement, "beneficiary_name", None),
        total_quantity=getattr(disbursement, "disbursement_quantity", None),
        program_mnemonic=getattr(disbursement_envelope, "benefit_program_mnemonic", None),
        program_description=None,  # Add if available
        target_registry=getattr(disbursement_envelope, "target_registry", None),
        disbursement_cycle_mnemonic=getattr(
            disbursement_envelope, "cycle_code_mnemonic", None
        ),
        disbursement_date=str(
            getattr(disbursement_envelope, "disbursement_schedule_date", None)
        ),
        benefit_code_id=getattr(disbursement_envelope, "benefit_code_id", None),
        benefit_code_mnemonic=getattr(disbursement_envelope, "benefit_code_mnemonic", None),
        benefit_type=getattr(disbursement_envelope, "benefit_type", None),
        measurement_unit=getattr(disbursement_envelope, "measurement_unit", None),
        benefit_description=None,  # Add if available
        warehouse_id=getattr(disbursement_resolution_geo_address, "warehouse_id", None),
        warehouse_mnemonic=getattr(disbursement_resolution_geo_address, "warehouse_mnemonic", None),
        agency_id=getattr(disbursement_resolution_geo_address, "agency_id", None),
        agency_mnemonic=getattr(disbursement_resolution_geo_address, "agency_mnemonic", None),
        agency_description=None,  # Add if available
        total_quantity=getattr(disbursement, "disbursement_quantity", None),
        administrative_zone_id_large=getattr(
            disbursement_resolution_geo_address, "administrative_zone_id_large", None
        ),
        administrative_zone_mnemonic_large=getattr(
            disbursement_resolution_geo_address, "administrative_zone_mnemonic_large", None
        ),
        administrative_zone_id_small=getattr(
            disbursement_resolution_geo_address, "administrative_zone_id_small", None
        ),
        administrative_zone_mnemonic_small=getattr(
            disbursement_resolution_geo_address, "administrative_zone_mnemonic_small", None
        ),
    )
    
    return notification_payload
