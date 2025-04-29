import logging
from datetime import datetime, timedelta

from openg2p_g2p_bridge_models.models import (
    BankDisbursementBatchStatus,
    CancellationStatus,
    DisbursementBatchControl,
    DisbursementEnvelope,
    DisbursementEnvelopeBatchStatus,
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


@celery_app.task(
    name="disburse_funds_from_bank_beat_producer",
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def disburse_funds_from_bank_beat_producer():
    _logger.info("Running disburse_funds_from_bank_beat_producer")
    session_maker = sessionmaker(bind=_engine, expire_on_commit=False)

    with session_maker() as session:
        # 1. Reset stale 'PROCESSING' batches back to 'PENDING'
        stale_at = datetime.now() - timedelta(
            minutes=_config.disbursement_retry_threshold_minutes
        )
        reset_stmt = (
            update(BankDisbursementBatchStatus)
            .where(
                BankDisbursementBatchStatus.disbursement_status
                == ProcessStatus.PROCESSING.value,
                BankDisbursementBatchStatus.updated_at < stale_at,
            )
            .values(disbursement_status=ProcessStatus.PENDING.value)
        )
        _logger.info(
            f"Resetting stale batches older than {stale_at} to PENDING"
        )
        session.execute(reset_stmt)
        session.commit()

        # 2. Fetch envelopes (streamed)
        date_condition = (
            DisbursementEnvelope.disbursement_schedule_date == datetime.now().date()
            if not _config.process_future_disbursement_schedules
            else literal(True)
        )
        stmt = (
            select(DisbursementEnvelope)
            .join(
                DisbursementEnvelopeBatchStatus,
                DisbursementEnvelope.disbursement_envelope_id
                == DisbursementEnvelopeBatchStatus.disbursement_envelope_id,
            )
            .filter(
                date_condition,
                DisbursementEnvelope.cancellation_status
                == CancellationStatus.Not_Cancelled.value,
                DisbursementEnvelope.number_of_disbursements
                == DisbursementEnvelopeBatchStatus.number_of_disbursements_received,
                DisbursementEnvelopeBatchStatus.funds_blocked_with_bank
                == FundsBlockedWithBankEnum.FUNDS_BLOCK_SUCCESS.value,
            )
            .limit(_config.no_of_disbursement_envelopes_to_process)
            .execution_options(stream_results=True)
        )

        envelopes = session.execute(stmt).scalars().yield_per(_config.batch_fetch_size)
        _logger.info(
            f"Found {len(list(envelopes))} envelopes to process"
        )

        for envelope in envelopes:
            # 3. Fetch pending batches for this envelope (streamed)
            pending_stmt = (
                select(BankDisbursementBatchStatus)
                .filter(
                    and_(
                        BankDisbursementBatchStatus.disbursement_envelope_id
                        == envelope.disbursement_envelope_id,
                        BankDisbursementBatchStatus.disbursement_status
                        == ProcessStatus.PENDING.value,
                        BankDisbursementBatchStatus.disbursement_attempts
                        < _config.funds_disbursement_attempts,
                    )
                )
                .limit(_config.no_of_disbursement_envelopes_to_process * 2)
                .execution_options(stream_results=True)
            )
            batches = (
                session.execute(pending_stmt)
                .scalars()
                .yield_per(_config.pending_batch_fetch_size)
            )
            _logger.info(
                f"Found {len(list(batches))} pending batches for envelope {envelope.disbursement_envelope_id}"
            )

            for batch in batches:
                # Skip if there are unprocessed controls
                control = (
                    session.query(DisbursementBatchControl)
                    .filter(
                        DisbursementBatchControl.bank_disbursement_batch_id
                        == batch.bank_disbursement_batch_id,
                        DisbursementBatchControl.mapper_status
                        != ProcessStatus.PROCESSED.value,
                    )
                    .first()
                )
                if control:
                    _logger.info(
                        f"Skipping batch {batch.bank_disbursement_batch_id}: unprocessed controls."
                    )
                    continue

                # Mark as processing and commit
                batch.disbursement_status = ProcessStatus.PROCESSING.value
                session.add(batch)
                _logger.info(
                    f"Marking batch {batch.bank_disbursement_batch_id} as processing."
                )
                try:
                    session.commit()
                except Exception:
                    session.rollback()
                    _logger.exception(
                        f"Failed to mark batch {batch.bank_disbursement_batch_id} as processing."
                    )
                    continue

                # Dispatch worker task
                _logger.info(
                    f"Dispatching task for batch {batch.bank_disbursement_batch_id}"
                )
                celery_app.send_task(
                    "disburse_funds_from_bank_worker",
                    args=(batch.bank_disbursement_batch_id,),
                    queue="g2p_bridge_celery_worker_tasks",
                )

    _logger.info("Finished disburse_funds_from_bank_beat_producer run.")
