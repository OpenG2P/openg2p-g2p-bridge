import logging
from openg2p_g2p_bridge_models.models import (
    DisbursementBatchControl,
    ProcessStatus,
)
from sqlalchemy import and_, select
from sqlalchemy.orm import sessionmaker

from ..app import celery_app, get_engine
from ..config import Settings

_config = Settings.get_config()
_engine = get_engine()
_logger = logging.getLogger("warehouse_allocation_beat_producer")

@celery_app.task(name="warehouse_allocation_beat_producer")
def warehouse_allocation_beat_producer():
    session_maker = sessionmaker(bind=_engine, expire_on_commit=False)
    with session_maker() as session:
        result = session.execute(
            select(DisbursementBatchControl).where(
                    DisbursementBatchControl.warehouse_allocation_status == ProcessStatus.PENDING,
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
            session.commit()
        _logger.info("Finished warehouse_allocation_beat_producer") 