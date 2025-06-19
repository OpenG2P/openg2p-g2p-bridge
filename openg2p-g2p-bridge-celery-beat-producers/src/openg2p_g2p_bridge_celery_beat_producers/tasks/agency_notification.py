import logging
from openg2p_g2p_bridge_models.models import (
    DisbursementBatchControlGeo,
    ProcessStatus,
)
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from ..config import Settings
from ..app import celery_app, get_engine

_engine = get_engine()
_config = Settings.get_config()
_logger = logging.getLogger("agency_notification_beat_producer")

@celery_app.task(name="agency_notification_beat_producer")
def agency_notification_beat_producer():
    session_maker = sessionmaker(bind=_engine, expire_on_commit=False)
    with session_maker() as session:
        result = session.execute(
            select(DisbursementBatchControlGeo).where(
                DisbursementBatchControlGeo.agency_notification_status == ProcessStatus.PENDING
            )
        )
        disbursement_batch_control_geos = result.scalars().all()
        for disbursement_batch_control_geo in disbursement_batch_control_geos:
            _logger.info(f"Sending agency_notification_worker task for disbursement_control_geo_id: {disbursement_batch_control_geo.disbursement_control_geo_id}")
            disbursement_batch_control_geo.agency_notification_status = ProcessStatus.PROCESSING
            celery_app.send_task(
                "agency_notification_worker",
                args=[disbursement_batch_control_geo.disbursement_control_geo_id],
                queue="g2p_bridge_celery_worker_tasks",
            )
            session.commit()
        _logger.info("Finished agency_notification_beat_producer") 
