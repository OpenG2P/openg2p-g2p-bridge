import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import sessionmaker

from sqlalchemy.future import select
from openg2p_g2p_bridge_models.models import (
    DisbursementBatchControl,
    DisbursementBatchControlGeo,
    DisbursementResolutionGeoAddress,
    ProcessStatus,
)
from openg2p_g2p_bridge_agency_allocator.agency_allocator.agency_allocator_factory import AgencyAllocatorFactory
from ..config import Settings
from ..app import get_engine, celery_app

_logger = logging.getLogger("agency_allocation_worker")
_engine = get_engine()
_config = Settings.get_config()

@celery_app.task(name="agency_allocation_worker")
def agency_allocation_worker(disbursement_batch_control_id: str) -> None:
    session_maker = sessionmaker(bind=_engine, expire_on_commit=False)
    with session_maker() as session:
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
            agency_allocator = AgencyAllocatorFactory.get_agency_allocator()
            allocation_results: List[Dict[str, Any]] = agency_allocator.allocate_agency([geo.__dict__ for geo in disbursement_batch_control_geos])
            # Persist results
            for disbursement_batch_control_geo, allocation in zip(disbursement_batch_control_geos, allocation_results):
                disbursement_batch_control_geo.agency_id = allocation["agency_id"]
                disbursement_batch_control_geo.agency_mnemonic = allocation["agency_mnemonic"]
                # Initial notification_status values
                disbursement_batch_control_geo.warehouse_notification_status = ProcessStatus.PENDING
                disbursement_batch_control_geo.agency_notification_status = ProcessStatus.PENDING

                # Bulk Update DisbursementResolutionGeoAddress
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
                    )
                )

            # Update batch control status
            disbursement_batch_control.agency_allocation_status = ProcessStatus.PROCESSED
            session.commit()
        except Exception as e:
            _logger.error(f"Agency allocation failed: {e}")
            # Update error code and attempts
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
                    disbursement_batch_control.agency_allocation_status = ProcessStatus.FAILED
                    # TODO: Do this ProcessStatus.FAILED status updation in all workers
                session.commit() 