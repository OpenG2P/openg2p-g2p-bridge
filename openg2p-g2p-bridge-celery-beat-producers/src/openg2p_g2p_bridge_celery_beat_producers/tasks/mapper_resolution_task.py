import logging
from datetime import datetime, timedelta

from openg2p_g2p_bridge_models.models import DisbursementBatchControl, ProcessStatus
from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker


from ..app import celery_app, get_engine
from ..config import Settings

_config = Settings.get_config()
_logger = logging.getLogger(_config.logging_default_logger_name)
_engine = get_engine()

@celery_app.task(name="mapper_resolution_beat_producer")
def mapper_resolution_beat_producer():
    """
    A Celery beat producer that periodically checks for disbursement batches
    that require mapper resolution and triggers the mapper resolution worker.
    """
    _logger.info("Mapper Resolution Producer running...")

    session_maker = sessionmaker(bind=_engine, expire_on_commit=False)
    with session_maker() as session:
        # Get the setting for stale tasks
        stale_at_setting = session.get(Settings, "stale_at")
        stale_at = (
            int(stale_at_setting.value) if stale_at_setting else (24 * 60 * 60)
        )  # Default to 24 hours
        stale_at_datetime = datetime.now() - timedelta(seconds=stale_at)

        # 1. Reset tasks that are in progress for too long (stale)
        session.execute(
            update(DisbursementBatchControl)
            .where(
                DisbursementBatchControl.fa_resolution_status == ProcessStatus.IN_PROGRESS,
                DisbursementBatchControl.updated_at < stale_at_datetime,
            )
            .values(fa_resolution_status=ProcessStatus.PENDING)
        )

        # 2. Select pending tasks
        pending_batches = session.scalars(
            select(DisbursementBatchControl).where(
                DisbursementBatchControl.fa_resolution_status == ProcessStatus.PENDING,
                DisbursementBatchControl.fa_resolution_attempts
                < _config.mapper_resolution_max_attempts,
            )
        ).all()

        if not pending_batches:
            _logger.info("No pending disbursement batches for mapper resolution.")
            return

        for batch in pending_batches:
            # 3. Mark as in progress
            batch.fa_resolution_status = ProcessStatus.IN_PROGRESS
            session.add(batch)
            session.commit()

            # 4. Publish to Celery queue
            celery_app.send_task(
                "mapper-resolution-worker",
                args=[batch.disbursement_batch_control_id],
            )
            _logger.info(
                f"Published disbursement batch {batch.disbursement_batch_control_id} to mapper-resolution-worker."
            )

        _logger.info(
            f"Published {len(pending_batches)} disbursement batches for mapper resolution."
        )
