import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import update
from sqlalchemy.orm import sessionmaker

from sqlalchemy.future import select
from openg2p_g2p_bridge_models.models import (
    DisbursementBatchControl,
    DisbursementBatchControlGeo,
    DisbursementResolutionGeoAddress,
    ProcessStatus,
    DisbursementEnvelope,
)
from openg2p_g2p_bridge_agency_allocator.agency_allocator.agency_allocator_factory import AgencyAllocatorFactory
from ..config import Settings
from ..app import get_engine, celery_app

_logger = logging.getLogger("agency_allocation_worker")
_engine = get_engine()
_config = Settings.get_config()
session_maker = sessionmaker(bind=_engine.get("db_engine_bridge"), expire_on_commit=False)
session_maker_pbms = sessionmaker(bind=_engine.get("db_engine_pbms"), expire_on_commit=False)  # TODO: Change engine if agency DB is different

@celery_app.task(name="agency_allocation_worker")
def agency_allocation_worker(disbursement_batch_control_id: str) -> None:
    with session_maker() as session, session_maker_pbms() as pbms_session:
        try:
            # Fetch the batch control record
            disbursement_batch_control: Optional[DisbursementBatchControl] = (
                session.execute(
                    select(DisbursementBatchControl).where(
                        DisbursementBatchControl.disbursement_batch_control_id == disbursement_batch_control_id
                    )
                )
            ).scalars().first()
            if not disbursement_batch_control:
                _logger.error(f"No batch control found for id {disbursement_batch_control_id}")
                return

            # Fetch all related geo records
            disbursement_batch_control_geos: List[DisbursementBatchControlGeo] = (
                session.execute(
                    select(DisbursementBatchControlGeo).where(
                        DisbursementBatchControlGeo.disbursement_batch_control_id == disbursement_batch_control_id
                    )
                )
            ).scalars().all()

            # Fetch the related envelope for benefit_code and program
            disbursement_envelope = session.execute(
                select(DisbursementEnvelope).where(
                    DisbursementEnvelope.disbursement_envelope_id == disbursement_batch_control.disbursement_envelope_id
                )
            ).scalars().first()
            if not disbursement_envelope:
                _logger.error(f"No envelope found for id {disbursement_batch_control.disbursement_envelope_id}")
                return

            # Prepare small_geo_list
            small_geo_list = [
                {
                    'batch_control_geo_id': geo.disbursement_control_geo_id,
                    'administrative_zone_id_small': geo.administrative_zone_id_small,
                    'administrative_zone_mnemonic_small': geo.administrative_zone_mnemonic_small,
                }
                for geo in disbursement_batch_control_geos
            ]
            benefit_code = {
                'id': disbursement_envelope.benefit_code_id,
                'mnemonic': disbursement_envelope.benefit_code_mnemonic,
            }
            program = {
                'id': disbursement_envelope.benefit_program_mnemonic,
                'mnemonic': disbursement_envelope.benefit_program_mnemonic,
            }

            agency_allocator = AgencyAllocatorFactory.get_agency_allocator()
            allocation_results: List[Dict[str, Any]] = agency_allocator.allocate_agency(
                pbms_session, small_geo_list, benefit_code, program
            )

            for disbursement_batch_control_geo, allocation in zip(disbursement_batch_control_geos, allocation_results):
                # Bulk update DisbursementBatchControlGeo
                session.execute(
                    update(DisbursementBatchControlGeo)
                    .where(
                        DisbursementBatchControlGeo.disbursement_control_geo_id == disbursement_batch_control_geo.disbursement_control_geo_id
                    )
                    .values(
                        agency_id=allocation["agency_id"],
                        agency_mnemonic=allocation["agency_mnemonic"],
                        agency_additional_attributes=allocation.get("agency_additional_attributes", {}),
                        warehouse_notification_status=ProcessStatus.PENDING,
                        agency_notification_status=ProcessStatus.PENDING,
                    )
                )

                # Bulk update DisbursementResolutionGeoAddress
                session.execute(
                    update(DisbursementResolutionGeoAddress)
                    .where(
                        DisbursementResolutionGeoAddress.disbursement_batch_control_id == disbursement_batch_control_geo.disbursement_batch_control_id,
                        DisbursementResolutionGeoAddress.administrative_zone_id_large == disbursement_batch_control_geo.administrative_zone_id_large,
                        DisbursementResolutionGeoAddress.administrative_zone_id_small == disbursement_batch_control_geo.administrative_zone_id_small,
                    )
                    .values(
                        agency_id=allocation["agency_id"],
                        agency_mnemonic=allocation["agency_mnemonic"],
                        beneficiary_notification_status=ProcessStatus.PENDING,
                    )
                )

            # Update batch control status
            disbursement_batch_control.agency_allocation_status = ProcessStatus.PROCESSED
            disbursement_batch_control.agency_allocation_attempts += 1
            disbursement_batch_control.agency_allocation_latest_error_code = None
            disbursement_batch_control.agency_allocation_timestamp = datetime.now()

            session.commit()
        except Exception as e:
            _logger.error(f"Agency allocation failed: {e}")
            disbursement_batch_control: Optional[DisbursementBatchControl] = (
                session.execute(
                    select(DisbursementBatchControl).where(
                        DisbursementBatchControl.disbursement_batch_control_id == disbursement_batch_control_id
                    )
                )
            ).scalars().first()
            if disbursement_batch_control:
                disbursement_batch_control.agency_allocation_latest_error_code = str(e)
                disbursement_batch_control.agency_allocation_attempts += 1
                if disbursement_batch_control.agency_allocation_attempts >= _config.agency_allocation_max_attempts:
                    disbursement_batch_control.agency_allocation_status = ProcessStatus.ERROR
                session.commit() 