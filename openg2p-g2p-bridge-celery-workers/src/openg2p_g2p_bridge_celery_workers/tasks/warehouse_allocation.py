import logging
from typing import List, Dict, Any, Optional
from openg2p_fastapi_common.context import dbengine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select
from openg2p_g2p_bridge_models.models import (
    DisbursementBatchControl,
    DisbursementBatchControlGeo,
    DisbursementResolutionGeoAddress,
    ProcessStatus,
)
from openg2p_g2p_bridge_celery_workers.app import celery_app
from openg2p_g2p_bridge_warehouse_allocator.warehouse_allocator.warehouse_allocator_factory import WarehouseAllocatorFactory

_logger = logging.getLogger("warehouse_allocation_worker")

@celery_app.task(name="warehouse_allocation_worker")
async def warehouse_allocation_worker(disbursement_batch_control_id: str) -> None:
    session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
    async with session_maker() as session:
        try:
            # Fetch the batch control record
            disbursement_batch_control: Optional[DisbursementBatchControl] = (
                await session.execute(
                    select(DisbursementBatchControl).where(
                        DisbursementBatchControl.disbursement_batch_control_id == disbursement_batch_control_id
                    )
                )
            ).scalars().first()
            if not disbursement_batch_control:
                _logger.error(f"No batch control found for id {disbursement_batch_control_id}")
                return
            # Fetch all related geo records
            geo_records: List[DisbursementBatchControlGeo] = (
                await session.execute(
                    select(DisbursementBatchControlGeo).where(
                        DisbursementBatchControlGeo.disbursement_batch_control_id == disbursement_batch_control_id
                    )
                )
            ).scalars().all()
            warehouse_allocator = WarehouseAllocatorFactory.get_warehouse_allocator()
            allocation_results: List[Dict[str, Any]] = warehouse_allocator.allocate_warehouse([geo.__dict__ for geo in geo_records])
            # Persist results
            for geo, allocation in zip(geo_records, allocation_results):
                geo.warehouse_id = allocation["warehouse_id"]
                geo.warehouse_mnemonic = allocation["warehouse_mnemonic"]
                # Initial notification_status values
                geo.warehouse_notification_status = ProcessStatus.PENDING
                geo.agency_notification_status = ProcessStatus.PENDING
                # Also persist to DisbursementResolutionGeoAddress
                res_geo = DisbursementResolutionGeoAddress(
                    disbursement_id=allocation["disbursement_id"],
                    disbursement_cycle_id=geo.disbursement_cycle_id,
                    disbursement_envelope_id=geo.disbursement_envelope_id,
                    disbursement_batch_control_id=geo.disbursement_batch_control_id,
                    beneficiary_id=allocation["beneficiary_id"],
                    administrative_zone_large=geo.administrative_zone_id_large,
                    administrative_zone_small=geo.administrative_zone_small,
                    warehouse_id=allocation["warehouse_id"],
                    warehouse_mnemonic=allocation["warehouse_mnemonic"],
                    agency_id=allocation.get("agency_id"),
                    agency_mnemonic=allocation.get("agency_mnemonic"),
                    beneficiary_notification_status=ProcessStatus.PENDING,
                )
                session.add(res_geo)
            # Update batch control status
            disbursement_batch_control.warehouse_allocation_status = ProcessStatus.PROCESSED
            disbursement_batch_control.agency_allocation_status = ProcessStatus.PENDING
            await session.commit()
        except Exception as e:
            _logger.error(f"Warehouse allocation failed: {e}")
            # Update error code and attempts
            if disbursement_batch_control:
                disbursement_batch_control.warehouse_allocation_latest_error_code = str(e)
                disbursement_batch_control.warehouse_allocation_attempts += 1
                await session.commit() 