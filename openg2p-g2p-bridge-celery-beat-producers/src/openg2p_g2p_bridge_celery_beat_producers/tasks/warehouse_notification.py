import logging
from openg2p_g2p_bridge_models.models import (
    DisbursementBatchControlGeo,
    ProcessStatus,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from openg2p_g2p_bridge_celery_beat_producers.app import celery_app
from ..config import Settings

_config = Settings.get_config()
_logger = logging.getLogger("warehouse_notification_beat_producer")

@celery_app.task(name="warehouse_notification_beat_producer")
async def warehouse_notification_beat_producer():
    session_maker = async_sessionmaker(_config.get_engine(), expire_on_commit=False)
    async with session_maker() as session:
        result = await session.execute(
            select(DisbursementBatchControlGeo).where(
                DisbursementBatchControlGeo.warehouse_notification_status == ProcessStatus.PENDING
            )
        )
        disbursement_batch_control_geos = result.scalars().all()
        for disbursement_batch_control_geo in disbursement_batch_control_geos:
            _logger.info(f"Sending warehouse_notification_worker task for disbursement_control_geo_id: {disbursement_batch_control_geo.disbursement_control_geo_id}")
            celery_app.send_task(
                "warehouse_notification_worker",
                args=[disbursement_batch_control_geo.disbursement_control_geo_id],
                queue="g2p_bridge_celery_worker_tasks",
            )
        _logger.info("Finished warehouse_notification_beat_producer") 