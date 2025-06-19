import logging
from datetime import datetime, timedelta

from openg2p_g2p_bridge_models.models import (
    CancellationStatus,
    DisbursementBatchControl,
    DisbursementEnvelope,
    EnvelopeBatchStatusForDigitalCash,
    EnvelopeControl,
    FundsBlockedWithBankEnum,
    ProcessStatus,
)
from sqlalchemy import and_, literal, select, update
from sqlalchemy.orm import sessionmaker

from ..app import celery_app, get_engine
from ..config import Settings

_config = Settings.get_config()
_logger = logging.getLogger(_config.logging_default_logger_name)
_engine = get_engine()


@celery_app.task(name="disburse_funds_from_bank_beat_producer")
def disburse_funds_from_bank_beat_producer():
    _logger.info("Running disburse_funds_from_bank_beat_producer")
    session_maker = sessionmaker(bind=_engine, expire_on_commit=False)
    with session_maker() as session:
        # 1. Reset stale 'PROCESSING' batches back to 'PENDING'
        stale_at = datetime.now() - timedelta(
            minutes=_config.task_stale_threshold_minutes
        )
        reset_stmt = (
            update(DisbursementBatchControl)
            .where(
                DisbursementBatchControl.sponsor_bank_dispatch_status
                == ProcessStatus.PROCESSING,
                DisbursementBatchControl.updated_at < stale_at,
            )
            .values(sponsor_bank_dispatch_status=ProcessStatus.PENDING)
        )
        session.execute(reset_stmt)
        session.commit()
        # Check if the disbursement schedule date is today if the configuration is
        # not set to process future disbursement schedules
        date_condition = (
            DisbursementEnvelope.disbursement_schedule_date == datetime.now().date()
            if not _config.process_future_disbursement_schedules
            else literal(True)
        )
        envelopes = (
            session.execute(
                select(DisbursementEnvelope)
                .join(
                    EnvelopeControl,
                    DisbursementEnvelope.disbursement_envelope_id
                    == EnvelopeControl.disbursement_envelope_id,
                )
                .join(
                    EnvelopeBatchStatusForDigitalCash,
                    DisbursementEnvelope.disbursement_envelope_id
                    == EnvelopeBatchStatusForDigitalCash.disbursement_envelope_id,
                )
                .filter(
                    date_condition,
                    DisbursementEnvelope.cancellation_status
                    == CancellationStatus.NOT_CANCELLED.value,
                    DisbursementEnvelope.number_of_disbursements
                    == EnvelopeControl.number_of_disbursements_received,
                    EnvelopeBatchStatusForDigitalCash.funds_blocked_with_bank
                    == FundsBlockedWithBankEnum.FUNDS_BLOCK_SUCCESS.value,
                )
                .limit(_config.no_of_tasks_to_process)
            )
            .scalars()
            .all()
        )
        for envelope in envelopes:

            disbursement_batch_controls: list[DisbursementBatchControl] = (
                session.execute(
                select(DisbursementBatchControl).filter(
                    DisbursementBatchControl.disbursement_envelope_id
                    == envelope.disbursement_envelope_id,
                    DisbursementBatchControl.sponsor_bank_dispatch_status
                    == ProcessStatus.PENDING,
                ).limit(_config.no_of_tasks_to_process)
            )
            .scalars()
            .all()
            )
            _logger.info(
                f"Found {len(disbursement_batch_controls)} pending batch controls for envelope {envelope.disbursement_envelope_id}"
            )

            for disbursement_batch_control in disbursement_batch_controls:
                _logger.info("Added batch to session")
                session.commit()
                celery_app.send_task(
                    "disburse_funds_from_bank_worker",
                    (disbursement_batch_control.disbursement_batch_control_id,),
                    queue="g2p_bridge_celery_worker_tasks",
                )
            _logger.info(
                f"Sent tasks to disburse funds for {len(disbursement_batch_controls)} batches"
            )
