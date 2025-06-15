import logging
from openg2p_g2p_bridge_models.models import (
    DisbursementBatchControl,
    ProcessStatus,
)
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from openg2p_g2p_bridge_celery_beat_producers.app import celery_app
from ..config import Settings

_config = Settings.get_config()
_logger = logging.getLogger("warehouse_allocation_beat_producer")

@celery_app.task(name="warehouse_allocation_beat_producer")
async def warehouse_allocation_beat_producer():
    session_maker = async_sessionmaker(_config.get_engine(), expire_on_commit=False)
    async with session_maker() as session:
        result = await session.execute(
            select(DisbursementBatchControl).where(
                and_(
                    DisbursementBatchControl.warehouse_allocation_status == ProcessStatus.PENDING,
                    DisbursementBatchControl.warehouse_allocation_attempts < _config.warehouse_allocation_max_attempts,
                )
            )
        )
        disbursement_batch_controls = result.scalars().all()
        for disbursement_batch_control in disbursement_batch_controls:
            _logger.info(f"{disbursement_batch_control.warehouse_allocation_attempts} / {_config.warehouse_allocation_max_attempts} attempts done")
            _logger.info(f"Sending warehouse_allocation_worker task for batch_control_id: {disbursement_batch_control.disbursement_batch_control_id}")
            disbursement_batch_control.warehouse_allocation_status = ProcessStatus.PROCESSING
            celery_app.send_task(
                "warehouse_allocation_worker",
                args=[disbursement_batch_control.disbursement_batch_control_id],
                queue="g2p_bridge_celery_worker_tasks",
            )
            await session.commit()
        _logger.info("Finished warehouse_allocation_beat_producer") 