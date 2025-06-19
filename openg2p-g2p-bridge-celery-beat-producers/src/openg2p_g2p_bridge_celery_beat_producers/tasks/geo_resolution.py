import logging

from openg2p_g2p_bridge_models.models import DisbursementBatchControl, ProcessStatus
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from ..app import celery_app, get_engine
from ..config import Settings

_config = Settings.get_config()
_logger = logging.getLogger(_config.logging_default_logger_name)
_engine = get_engine()


@celery_app.task(name="geo_resolution_beat_producer")
def geo_resolution_beat_producer():
    _logger.info("Checking for disbursement batches to perform geo resolution")
    session_maker = sessionmaker(bind=_engine, expire_on_commit=False)

    with session_maker() as session:
        batches = (
            session.execute(
                select(DisbursementBatchControl)
                .filter(
                    DisbursementBatchControl.geo_resolution_status
                    == ProcessStatus.PENDING,
                    DisbursementBatchControl.geo_resolution_attempts
                    < _config.geo_resolution_max_attempts,
                )
                .limit(_config.no_of_tasks_to_process)
            )
            .scalars()
            .all()
        )

        for batch in batches:
            _logger.info(
                f"Sending geo resolution task for batch: {batch.disbursement_batch_control_id}"
            )

            batch.geo_resolution_status = ProcessStatus.PROCESSING

            celery_app.send_task(
                "geo_resolution_worker",
                args=(batch.disbursement_batch_control_id,),
                queue="g2p_bridge_celery_worker_tasks",
            )
            session.commit()

        _logger.info("Completed checking for disbursement batches to perform geo resolution") 