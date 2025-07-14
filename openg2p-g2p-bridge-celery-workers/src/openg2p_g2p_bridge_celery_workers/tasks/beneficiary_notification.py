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

NOTIFICATION_SERVICE_URL = _config.notification_service_url


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
            # Build BeneficiaryEntitlement
            beneficiary_entitlement = BeneficiaryEntitlement(
                beneficiary_id=disbursement_resolution_geo_address.beneficiary_id,
                beneficiary_name=getattr(disbursement, "beneficiary_name", None)
                if disbursement
                else None,
                total_quantity=getattr(disbursement, "disbursement_quantity", None)
                if disbursement
                else None,
            )
            # Build notification payload
            notification_payload = BeneficiaryNotificationPayload(
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
                total_quantity=getattr(disbursement, "disbursement_quantity", None)
                if disbursement
                else None,
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
                beneficiary_entitlement=beneficiary_entitlement,
            )
            # Create NotificationLog entry (PENDING)
            notification_log = NotificationLog(
                notification_type=NotificationType.BENEFICIARY_NOTIFICATION.value,
                recipient=disbursement_resolution_geo_address.beneficiary_id,
                payload=str(notification_payload.model_dump()),
                sent_at=datetime.datetime.now(),
            )
            session.add(notification_log)
            session.commit()

            # Send to notification microservice
            notifier = NotificationFactory.get_notifier()
            recipient = Recipient(
                recipient_id=disbursement_resolution_geo_address.beneficiary_id,
                recipient_name=disbursement_resolution_geo_address.beneficiary_name,
                recipient_email=disbursement_resolution_geo_address.beneficiary_email,
                recipient_phone=disbursement_resolution_geo_address.beneficiary_phone,
            )
            try:
                notification_response: NotificationResponse = notifier.send_notification(
                    notification_id=notification_log.id,
                    payload=notification_payload.model_dump(),
                    notification_type=NotificationType.BENEFICIARY_NOTIFICATION.value,
                    recipient=recipient
                )
                if notification_response.status == NotificationResponseStatus.FAILURE:
                    raise Exception(notification_response.error_message or "Notification failed")
                
                notification_log.status = notification_response.status.value
                notification_log.response = notification_response.response if notification_response else "SENT"
                notification_log.processed_at = datetime.datetime.now()
                disbursement_resolution_geo_address.beneficiary_notification_status = ProcessStatus.PROCESSED.value
            except Exception as e:
                notification_log.status = "ERROR"
                notification_log.error_message = str(e)
                notification_log.processed_at = datetime.datetime.now()
                _logger.error(f"Beneficiary notification failed: {e}")
                raise e
            session.commit()
        except Exception as e:
            session.rollback()
            _logger.error(f"Beneficiary notification failed: {e}")
            if disbursement_resolution_geo_address:
                disbursement_resolution_geo_address.beneficiary_notification_attempts += 1
                disbursement_resolution_geo_address.beneficiary_notification_latest_error_code = str(e)
                disbursement_resolution_geo_address.beneficiary_notification_status = ProcessStatus.PENDING.value

            if disbursement_resolution_geo_address.beneficiary_notification_attempts >= _config.beneficiary_notification_max_attempts:
                disbursement_resolution_geo_address.beneficiary_notification_status = ProcessStatus.ERROR.value
                session.commit()
