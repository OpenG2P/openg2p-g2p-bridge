import logging
from openg2p_g2p_bridge_models.models import (
    DisbursementResolutionGeoAddress,
    ProcessStatus,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from openg2p_g2p_bridge_celery_beat_producers.app import celery_app
from ..config import Settings

_config = Settings.get_config()
_logger = logging.getLogger("beneficiary_notification_beat_producer")

@celery_app.task(name="beneficiary_notification_beat_producer")
async def beneficiary_notification_beat_producer():
    session_maker = async_sessionmaker(_config.get_engine(), expire_on_commit=False)
    async with session_maker() as session:
        result = await session.execute(
            select(DisbursementResolutionGeoAddress).where(
                DisbursementResolutionGeoAddress.beneficiary_notification_status == ProcessStatus.PENDING
            )
        )
        disbursement_resolution_geo_addresses = result.scalars().all()
        for disbursement_resolution_geo_address in disbursement_resolution_geo_addresses:
            _logger.info(f"Sending beneficiary_notification_worker task for disbursement_id: {disbursement_resolution_geo_address.disbursement_id}")
            celery_app.send_task(
                "beneficiary_notification_worker",
                args=[disbursement_resolution_geo_address.disbursement_id],
                queue="g2p_bridge_celery_worker_tasks",
            )
        _logger.info("Finished beneficiary_notification_beat_producer") 