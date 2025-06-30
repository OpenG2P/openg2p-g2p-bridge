import asyncio
import datetime
import logging
import uuid
from typing import Optional

from openg2p_g2p_bridge_models.models import (
    Disbursement,
    DisbursementBatchControlGeo,
    DisbursementEnvelope,
    DisbursementResolutionGeoAddress,
    NotificationLog,
    NotificationStatus,
    ProcessStatus,
)
from openg2p_g2p_bridge_models.schemas import (
    AgencyNotificationPayload,
    BeneficiaryEntitlement,
    NotificationRequest,
    NotificationType,
)
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from ..app import celery_app, get_engine
from ..config import Settings
from ..helpers.notification_helper import NotificationHelper

_config = Settings.get_config()
_engine = get_engine()

NOTIFICATION_SERVICE_URL = _config.notification_service_url

_logger = logging.getLogger("agency_notification_worker")


@celery_app.task(name="agency_notification_worker")
def agency_notification_worker(disbursement_control_geo_id: str) -> None:
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
                            DisbursementBatchControlGeo.disbursement_control_geo_id
                            == disbursement_control_geo_id
                        )
                    )
                )
                .scalars()
                .first()
            )
            if not disbursement_batch_control_geo:
                _logger.error(
                    f"No batch control geo found for id {disbursement_control_geo_id}"
                )
                return
            # Fetch the related DisbursementEnvelope
            disbursement_envelope = (
                (
                    session.execute(
                        select(DisbursementEnvelope).where(
                            DisbursementEnvelope.disbursement_envelope_id
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

            # Fetch all DisbursementResolutionGeoAddress records for this agency/zone
            geo_addresses = (
                session.execute(
                    select(DisbursementResolutionGeoAddress).where(
                        DisbursementResolutionGeoAddress.disbursement_batch_control_geo_id
                        == disbursement_batch_control_geo.disbursement_control_geo_id
                    )
                )
                .scalars()
                .all()
            )

            # Fetch Disbursement records for these beneficiaries
            beneficiary_ids = [
                geo_address.beneficiary_id for geo_address in geo_addresses
            ]
            disbursements = (
                session.execute(
                    select(Disbursement).where(
                        Disbursement.beneficiary_id.in_(beneficiary_ids)
                    )
                )
                .scalars()
                .all()
            )
            disbursement_map = {
                (d.beneficiary_id, d.disbursement_id): d for d in disbursements
            }

            beneficiary_entitlements = []
            for geo_address in geo_addresses:
                # Try to find the matching Disbursement by beneficiary_id and disbursement_id if available
                disbursement = disbursement_map.get(
                    (
                        geo_address.beneficiary_id,
                        getattr(geo_address, "disbursement_id", None),
                    )
                )
                beneficiary_entitlements.append(
                    BeneficiaryEntitlement(
                        beneficiary_id=geo_address.beneficiary_id,
                        beneficiary_name=getattr(disbursement, "beneficiary_name", None)
                        if disbursement
                        else None,
                        total_quantity=getattr(
                            disbursement, "disbursement_quantity", None
                        )
                        if disbursement
                        else None,
                    )
                )

            # Build notification payload
            notification_payload = AgencyNotificationPayload(
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
                beneficiary_entitlements=beneficiary_entitlements,
            )

            # Create NotificationLog entry (PENDING)
            notification_log = NotificationLog(
                notification_id=str(uuid.uuid4()),
                notification_type=NotificationType.AGENCY_NOTIFICATION.value,
                recipient=disbursement_batch_control_geo.agency_mnemonic,
                payload=str(notification_payload.model_dump()),
                status=NotificationStatus.PENDING.value,
                sent_at=datetime.datetime.now(),
            )
            session.add(notification_log)
            session.commit()
            # Build NotificationRequest object
            notification_request = NotificationRequest(
                notification_type=NotificationType.AGENCY_NOTIFICATION.value,
                recipient=disbursement_batch_control_geo.agency_mnemonic,
                recipient_type="AGENCY",
                notification_payload=notification_payload,
                disbursement_control_geo_id=disbursement_batch_control_geo.disbursement_control_geo_id,
                agency_mnemonic=disbursement_batch_control_geo.agency_mnemonic,
                notification_request_id=notification_log.notification_id,
            )
            # Send to notification microservice
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
                disbursement_batch_control_geo.agency_notification_status = (
                    ProcessStatus.PROCESSED.value
                )
            except Exception as e:
                notification_log.status = NotificationStatus.ERROR.value
                notification_log.error_message = str(e)
                notification_log.processed_at = datetime.datetime.now()
                disbursement_batch_control_geo.agency_notification_status = (
                    ProcessStatus.ERROR.value
                )
                _logger.error(f"Agency notification failed: {e}")
            session.commit()
        except Exception as e:
            _logger.error(f"Agency notification failed: {e}")
            if disbursement_batch_control_geo:
                disbursement_batch_control_geo.agency_notification_status = (
                    ProcessStatus.ERROR.value
                )
                session.commit()
