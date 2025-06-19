import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.orm import sessionmaker
from openg2p_g2p_bridge_models.models import (
    DisbursementBatchControl,
    DisbursementBatchControlGeo,
    DisbursementResolutionGeoAddress,
    ProcessStatus,
)
from openg2p_g2p_bridge_warehouse_allocator.warehouse_allocator.warehouse_allocator_factory import WarehouseAllocatorFactory
from ..app import celery_app, get_engine
from ..config import Settings

_logger = logging.getLogger("warehouse_allocation_worker")
_engine = get_engine()
_config = Settings.get_config()


@celery_app.task(name="warehouse_allocation_worker")
def warehouse_allocation_worker(disbursement_batch_control_id: str) -> None:
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

            warehouse_allocator = WarehouseAllocatorFactory.get_warehouse_allocator()
            allocation_results: List[Dict[str, Any]] = warehouse_allocator.allocate_warehouse(
                [geo.__dict__ for geo in disbursement_batch_control_geos]
            )

            for disbursement_batch_control_geo, allocation in zip(disbursement_batch_control_geos, allocation_results):
                # Bulk update DisbursementBatchControlGeo
                session.execute(
                    update(DisbursementBatchControlGeo)
                    .where(
                        DisbursementBatchControlGeo.disbursement_control_geo_id == disbursement_batch_control_geo.disbursement_control_geo_id
                    )
                    .values(
                        warehouse_id=allocation["warehouse_id"],
                        warehouse_mnemonic=allocation["warehouse_mnemonic"],
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
                        warehouse_id=allocation["warehouse_id"],
                        warehouse_mnemonic=allocation["warehouse_mnemonic"],
                    )
                )

            # Update batch control status
            disbursement_batch_control.warehouse_allocation_status = ProcessStatus.PROCESSED
            disbursement_batch_control.warehouse_allocation_latest_error_code = None
            disbursement_batch_control.warehouse_allocation_attempts += 1
            disbursement_batch_control.warehouse_allocation_timestamp = datetime.now()
            disbursement_batch_control.agency_allocation_status = ProcessStatus.PENDING
            session.commit()
        except Exception as e:
            _logger.error(f"Warehouse allocation failed: {e}")
            # Update error code and attempts
            if disbursement_batch_control:
                disbursement_batch_control.warehouse_allocation_latest_error_code = str(e)
                disbursement_batch_control.warehouse_allocation_attempts += 1
                if disbursement_batch_control.warehouse_allocation_attempts >= _config.warehouse_allocation_max_attempts:
                    disbursement_batch_control.warehouse_allocation_status = ProcessStatus.ERROR
                session.commit() 