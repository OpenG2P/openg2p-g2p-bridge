import logging
from datetime import datetime
from typing import List, Optional

from openg2p_g2p_bridge_geo_resolver.geo_interface.geo_resolver_interface import GeoResolver
from openg2p_g2p_bridge_geo_resolver.geo_resolver.geo_resolution_factory import GeoResolutionFactory
from openg2p_g2p_bridge_models.models import (
    Disbursement,
    DisbursementBatchControl,
    DisbursementBatchControlGeo,
    DisbursementResolutionGeoAddress,
    ProcessStatus,
)
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
import uuid

from ..app import celery_app, get_engine
from ..config import Settings

_config = Settings.get_config()
_logger = logging.getLogger(_config.logging_default_logger_name)
_engine = get_engine()


@celery_app.task(name="geo_resolution_worker")
def geo_resolution_worker(disbursement_batch_control_id: str):
    _logger.info(f"Starting geo resolution for batch: {disbursement_batch_control_id}")
    session_maker = sessionmaker(bind=_engine, expire_on_commit=False)

    with session_maker() as session:
        try:
            disbursement_batch_control: Optional[DisbursementBatchControl] = (
                session.execute(
                    select(DisbursementBatchControl).where(
                        DisbursementBatchControl.disbursement_batch_control_id == disbursement_batch_control_id
                    )
                )
                .scalar_one_or_none()
            )

            if not disbursement_batch_control:
                _logger.error(f"No DisbursementBatchControl found for id {disbursement_batch_control_id}")
                return

            disbursements: List[Disbursement] = (
                session.execute(
                    select(Disbursement).where(
                        Disbursement.disbursement_batch_control_id == disbursement_batch_control_id
                    )
                )
                .scalars()
                .all()
            )

            if not disbursements:
                _logger.warning(f"No disbursements found for batch {disbursement_batch_control_id}")
                disbursement_batch_control.geo_resolution_status = ProcessStatus.PROCESSED
                disbursement_batch_control.warehouse_allocation_status = ProcessStatus.PENDING
                session.commit()
                return

            batch_beneficiary_list = [
                {
                    "disbursement_id": d.disbursement_id,
                    "beneficiary_id": d.beneficiary_id,
                }
                for d in disbursements
            ]

            geo_resolver: GeoResolver = GeoResolutionFactory.get_geo_resolver()
            resolved_data = geo_resolver.resolve_geo(batch_beneficiary_list)

            # Create a map of disbursement_id to disbursement_quantity for quick lookup
            disbursement_quantities = {d.disbursement_id: d.disbursement_quantity for d in disbursements}

            # A dictionary to hold aggregated data for DisbursementBatchControlGeo
            # Key: (administrative_zone_id_large, administrative_zone_id_small)
            batch_control_geo_map = {}

            for geo_resolution_item in resolved_data:
                key = (geo_resolution_item["administrative_zone_id_large"], geo_resolution_item["administrative_zone_id_small"])
                if key not in batch_control_geo_map:
                    batch_control_geo_map[key] = {
                        "total_quantity": 0,
                        "administrative_zone_mnemonic_large": geo_resolution_item["administrative_zone_mnemonic_large"],
                        "administrative_zone_mnemonic_small": geo_resolution_item["administrative_zone_mnemonic_small"],
                    }

                quantity = disbursement_quantities.get(geo_resolution_item["disbursement_id"], 0)
                batch_control_geo_map[key]["total_quantity"] += quantity

            disbursement_batch_control_geos = []
            batch_control_geo_id_map = {}
            for (admin_large_id, admin_small_id), data in batch_control_geo_map.items():
                disbursement_control_geo_id = str(uuid.uuid4())
                disbursement_batch_control_geo = DisbursementBatchControlGeo(
                    disbursement_control_geo_id=disbursement_control_geo_id,
                    disbursement_cycle_id=disbursement_batch_control.disbursement_cycle_id,
                    disbursement_envelope_id=disbursement_batch_control.disbursement_envelope_id,
                    disbursement_batch_control_id=disbursement_batch_control.disbursement_batch_control_id,
                    administrative_zone_id_large=admin_large_id,
                    administrative_zone_mnemonic_large=data["administrative_zone_mnemonic_large"],
                    administrative_zone_id_small=admin_small_id,
                    administrative_zone_mnemonic_small=data["administrative_zone_mnemonic_small"],
                    no_of_beneficiaries=len([item for item in resolved_data if item["administrative_zone_id_large"] == admin_large_id and item["administrative_zone_id_small"] == admin_small_id]),
                    total_quantity=data["total_quantity"],
                    warehouse_notification_status=ProcessStatus.NOT_APPLICABLE,
                    agency_notification_status=ProcessStatus.NOT_APPLICABLE,
                    active=True,
                )
                disbursement_batch_control_geos.append(disbursement_batch_control_geo)
                batch_control_geo_id_map[(admin_large_id, admin_small_id)] = disbursement_control_geo_id

            session.add_all(disbursement_batch_control_geos)
            session.flush()  # Ensure IDs are available

            # Now create DisbursementResolutionGeoAddress with the correct disbursement_batch_control_geo_id
            disbursement_resolution_geo_addresses = []
            for geo_resolution_item in resolved_data:
                key = (
                    geo_resolution_item["administrative_zone_id_large"],
                    geo_resolution_item["administrative_zone_id_small"],
                )
                disbursement_batch_control_geo_id = batch_control_geo_id_map.get(key)
                disbursement_resolution_geo_address = DisbursementResolutionGeoAddress(
                    disbursement_id=geo_resolution_item["disbursement_id"],
                    disbursement_cycle_id=disbursement_batch_control.disbursement_cycle_id,
                    disbursement_envelope_id=disbursement_batch_control.disbursement_envelope_id,
                    disbursement_batch_control_id=disbursement_batch_control.disbursement_batch_control_id,
                    disbursement_batch_control_geo_id=disbursement_batch_control_geo_id,
                    beneficiary_id=geo_resolution_item["beneficiary_id"],
                    administrative_zone_id_large=geo_resolution_item["administrative_zone_id_large"],
                    administrative_zone_mnemonic_large=geo_resolution_item["administrative_zone_mnemonic_large"],
                    administrative_zone_id_small=geo_resolution_item["administrative_zone_id_small"],
                    administrative_zone_mnemonic_small=geo_resolution_item["administrative_zone_mnemonic_small"],
                    active=True,
                )
                disbursement_resolution_geo_addresses.append(disbursement_resolution_geo_address)

            session.add_all(disbursement_resolution_geo_addresses)
            
            # Update the DisbursementBatchControl status

            disbursement_batch_control.geo_resolution_status = ProcessStatus.PROCESSED
            disbursement_batch_control.warehouse_allocation_status = ProcessStatus.PENDING
            disbursement_batch_control.geo_resolution_timestamp = datetime.now()
            disbursement_batch_control.geo_resolution_latest_error_code = None
            disbursement_batch_control.geo_resolution_attempts = (disbursement_batch_control.geo_resolution_attempts or 0) + 1
            
            session.commit()
            _logger.info(f"Successfully completed geo resolution for batch: {disbursement_batch_control_id}")

        except Exception as e:
            if 'session' in locals() and session.is_active:
                session.rollback()
            _logger.error(f"Error in geo resolution for batch {disbursement_batch_control_id}: {e}", exc_info=True)
            with session_maker() as error_session:
                # Use a new session for update to avoid issues with the failed session
                disbursement_batch_control_to_update = error_session.query(DisbursementBatchControl).filter_by(disbursement_batch_control_id=disbursement_batch_control_id).first()
                if disbursement_batch_control_to_update:
                    disbursement_batch_control_to_update.geo_resolution_status = ProcessStatus.PENDING
                    disbursement_batch_control_to_update.geo_resolution_latest_error_code = str(e)
                    disbursement_batch_control_to_update.geo_resolution_attempts = (disbursement_batch_control_to_update.geo_resolution_attempts or 0) + 1
                    if disbursement_batch_control_to_update.geo_resolution_attempts >= _config.geo_resolution_max_attempts:
                        disbursement_batch_control_to_update.geo_resolution_status = ProcessStatus.ERROR
                        disbursement_batch_control_to_update.geo_resolution_latest_error_code = str(e)
                    error_session.commit() 