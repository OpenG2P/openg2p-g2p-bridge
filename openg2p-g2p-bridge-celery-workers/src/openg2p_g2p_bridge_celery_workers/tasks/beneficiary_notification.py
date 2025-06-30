import datetime
import logging
import uuid
from typing import Optional

from openg2p_g2p_bridge_models.models import (
    Disbursement,
    DisbursementEnvelope,
    DisbursementResolutionGeoAddress,
    NotificationLog,
    NotificationStatus,
    ProcessStatus,
)
from openg2p_g2p_bridge_models.schemas import (
    BeneficiaryEntitlement,
    BeneficiaryNotificationPayload,
    NotificationRequest,
    NotificationType,
)
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from ..app import celery_app, get_engine
from ..config import Settings
from ..helpers import NotificationHelper

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
            geo_address: Optional[DisbursementResolutionGeoAddress] = (
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
            if not geo_address:
                _logger.error(
                    f"No geo address found for disbursement_id {disbursement_id}"
                )
                return
            # Fetch the envelope for payload details
            envelope: Optional[DisbursementEnvelope] = (
                (
                    session.execute(
                        select(DisbursementEnvelope).where(
                            DisbursementEnvelope.disbursement_envelope_id
                            == geo_address.disbursement_envelope_id
                        )
                    )
                )
                .scalars()
                .first()
            )
            if not envelope:
                _logger.error(
                    f"No envelope found for id {geo_address.disbursement_envelope_id}"
                )
                return
            # Fetch the Disbursement for beneficiary_name and disbursement_quantity
            disbursement: Optional[Disbursement] = (
                (
                    session.execute(
                        select(Disbursement).where(
                            Disbursement.disbursement_id == disbursement_id
                        )
                    )
                )
                .scalars()
                .first()
            )
            # Build BeneficiaryEntitlement
            beneficiary_entitlement = BeneficiaryEntitlement(
                beneficiary_id=geo_address.beneficiary_id,
                beneficiary_name=getattr(disbursement, "beneficiary_name", None)
                if disbursement
                else None,
                total_quantity=getattr(disbursement, "disbursement_quantity", None)
                if disbursement
                else None,
            )
            # Build notification payload
            notification_payload = BeneficiaryNotificationPayload(
                program_mnemonic=getattr(envelope, "benefit_program_mnemonic", None),
                program_description=None,  # Add if available
                target_registry=getattr(envelope, "target_registry", None),
                disbursement_cycle_mnemonic=getattr(
                    envelope, "cycle_code_mnemonic", None
                ),
                disbursement_date=str(
                    getattr(envelope, "disbursement_schedule_date", None)
                ),
                benefit_code_id=getattr(envelope, "benefit_code_id", None),
                benefit_code_mnemonic=getattr(envelope, "benefit_code_mnemonic", None),
                benefit_type=getattr(envelope, "benefit_type", None),
                measurement_unit=getattr(envelope, "measurement_unit", None),
                benefit_description=None,  # Add if available
                warehouse_id=getattr(geo_address, "warehouse_id", None),
                warehouse_mnemonic=getattr(geo_address, "warehouse_mnemonic", None),
                agency_id=getattr(geo_address, "agency_id", None),
                agency_mnemonic=getattr(geo_address, "agency_mnemonic", None),
                agency_description=None,  # Add if available
                total_quantity=getattr(disbursement, "disbursement_quantity", None)
                if disbursement
                else None,
                administrative_zone_id_large=getattr(
                    geo_address, "administrative_zone_id_large", None
                ),
                administrative_zone_mnemonic_large=getattr(
                    geo_address, "administrative_zone_mnemonic_large", None
                ),
                administrative_zone_id_small=getattr(
                    geo_address, "administrative_zone_id_small", None
                ),
                administrative_zone_mnemonic_small=getattr(
                    geo_address, "administrative_zone_mnemonic_small", None
                ),
                beneficiary_entitlement=beneficiary_entitlement,
            )
            # Create NotificationLog entry (PENDING)
            notification_log = NotificationLog(
                notification_id=str(uuid.uuid4()),
                notification_type=NotificationType.BENEFICIARY_NOTIFICATION.value,
                recipient=geo_address.beneficiary_id,
                payload=str(notification_payload.model_dump()),
                status=NotificationStatus.PENDING.value,
                sent_at=datetime.datetime.now(),
            )
            session.add(notification_log)
            session.commit()
            # Build NotificationRequest object
            notification_request = NotificationRequest(
                notification_type=NotificationType.BENEFICIARY_NOTIFICATION.value,
                recipient=geo_address.beneficiary_id,
                recipient_type="BENEFICIARY",
                notification_payload=notification_payload,
                beneficiary_id=geo_address.beneficiary_id,
                disbursement_id=geo_address.disbursement_id,
                notification_request_id=notification_log.notification_id,
            )
            # Send to notification microservice
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            helper = NotificationHelper()
            try:
                response = loop.run_until_complete(
                    helper.send_notification(
                        NOTIFICATION_SERVICE_URL,
                        notification_request=notification_request,
                    )
                )
                notification_log.status = NotificationStatus.PROCESSED.value
                notification_log.response = str(response.text)
                notification_log.processed_at = datetime.datetime.now()
                geo_address.beneficiary_notification_status = ProcessStatus.PROCESSED.value
            except Exception as e:
                notification_log.status = NotificationStatus.ERROR.value
                notification_log.error_message = str(e)
                notification_log.processed_at = datetime.datetime.now()
                geo_address.beneficiary_notification_status = ProcessStatus.ERROR.value
                _logger.error(f"Beneficiary notification failed: {e}")
            session.commit()
        except Exception as e:
            _logger.error(f"Beneficiary notification failed: {e}")
            if geo_address:
                geo_address.beneficiary_notification_status = ProcessStatus.ERROR.value
                session.commit()
