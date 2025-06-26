import logging
import random
import time
from datetime import datetime

from openg2p_g2p_bridge_bank_connectors.bank_connectors import BankConnectorFactory
from openg2p_g2p_bridge_bank_connectors.bank_interface.bank_connector_interface import (
    BankConnectorInterface,
    DisbursementPaymentPayload,
    PaymentStatus,
)
from openg2p_g2p_bridge_models.models import (
    BenefitProgramConfiguration,
    Disbursement,
    DisbursementBatchControl,
    DisbursementEnvelope,
    DisbursementResolutionFinancialAddress,
    EnvelopeBatchStatusForDigitalCash,
    ProcessStatus,
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from ..app import celery_app, get_engine
from ..config import Settings

_config = Settings.get_config()
_logger = logging.getLogger(_config.logging_default_logger_name)
_engine = get_engine()


@celery_app.task(name="disburse_funds_from_bank_worker")
def disburse_funds_from_bank_worker(disbursement_batch_control_id: str):
    _logger.info(
        f"Disbursing funds with bank for batch: {disbursement_batch_control_id}"
    )
    session_maker = sessionmaker(
        bind=_engine.get("db_engine_bridge"), expire_on_commit=False
    )

    with session_maker() as session:
        disbursement_batch_control = (
            session.query(DisbursementBatchControl)
            .filter(
                DisbursementBatchControl.disbursement_batch_control_id
                == disbursement_batch_control_id,
            )
            .first()
        )

        disbursement_envelope_id = disbursement_batch_control.disbursement_envelope_id
        envelope = (
            session.query(DisbursementEnvelope)
            .filter(
                DisbursementEnvelope.disbursement_envelope_id
                == disbursement_envelope_id
            )
            .first()
        )
        if not envelope:
            _logger.error(f"No DisbursementEnvelope {disbursement_envelope_id}")
            return

        envelope_batch_status_for_digital_cash = (
            session.query(EnvelopeBatchStatusForDigitalCash)
            .filter(
                EnvelopeBatchStatusForDigitalCash.disbursement_envelope_id
                == disbursement_envelope_id
            )
            .first()
        )
        if not envelope_batch_status_for_digital_cash:
            _logger.error(
                f"No EnvelopeBatchStatusForDigitalCash for {disbursement_envelope_id}"
            )
            return

        disbursements = (
            session.query(Disbursement)
            .filter(
                Disbursement.disbursement_batch_control_id
                == disbursement_batch_control_id
            )
            .all()
        )

        benefit_program_configuration = (
            session.query(BenefitProgramConfiguration)
            .filter(
                BenefitProgramConfiguration.benefit_program_mnemonic
                == envelope.benefit_program_mnemonic
            )
            .first()
        )

        disbursement_payment_payloads = []

        for disbursement in disbursements:
            disbursement_resolution_financial_address = (
                session.query(DisbursementResolutionFinancialAddress)
                .filter(
                    DisbursementResolutionFinancialAddress.disbursement_id
                    == disbursement.disbursement_id
                )
                .first()
            )

            disbursement_payment_payloads.append(
                DisbursementPaymentPayload(
                    disbursement_id=disbursement.disbursement_id,
                    remitting_account=benefit_program_configuration.sponsor_bank_account_number,
                    remitting_account_currency=benefit_program_configuration.sponsor_bank_account_currency,
                    payment_amount=disbursement.disbursement_quantity,
                    funds_blocked_reference_number=envelope_batch_status_for_digital_cash.funds_blocked_reference_number,
                    beneficiary_account=disbursement_resolution_financial_address.bank_account_number
                    if disbursement_resolution_financial_address
                    else None,
                    beneficiary_account_currency=benefit_program_configuration.sponsor_bank_account_currency,
                    beneficiary_bank_code=disbursement_resolution_financial_address.bank_code
                    if disbursement_resolution_financial_address
                    else None,
                    beneficiary_branch_code=disbursement_resolution_financial_address.branch_code
                    if disbursement_resolution_financial_address
                    else None,
                    payment_date=str(datetime.date(datetime.now())),
                    beneficiary_id=disbursement.beneficiary_id,
                    beneficiary_name=disbursement.beneficiary_name,
                    beneficiary_account_type=disbursement_resolution_financial_address.mapper_resolved_fa_type,
                    beneficiary_phone_no=disbursement_resolution_financial_address.mobile_number
                    if disbursement_resolution_financial_address
                    else None,
                    beneficiary_mobile_wallet_provider=disbursement_resolution_financial_address.mobile_wallet_provider
                    if disbursement_resolution_financial_address
                    else None,
                    beneficiary_email_wallet_provider=disbursement_resolution_financial_address.email_wallet_provider
                    if disbursement_resolution_financial_address
                    else None,
                    beneficiary_email=disbursement_resolution_financial_address.email_address
                    if disbursement_resolution_financial_address
                    else None,
                    disbursement_narrative=disbursement.narrative,
                    benefit_program_mnemonic=envelope.benefit_program_mnemonic,
                    cycle_code_mnemonic=envelope.cycle_code_mnemonic,
                )
            )
        # End of for loop

        bank_connector: BankConnectorInterface = (
            BankConnectorFactory.get_component().get_bank_connector(
                benefit_program_configuration.sponsor_bank_code
            )
        )

        envelope = (
            session.query(DisbursementEnvelope)
            .filter(
                DisbursementEnvelope.disbursement_envelope_id
                == disbursement_envelope_id
            )
            .first()
        )
        if not envelope:
            _logger.error(f"No DisbursementEnvelope {disbursement_envelope_id}")
            return

        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                _logger.info(
                    f"Locking envelope {disbursement_envelope_id}, attempt {attempt} / {max_retries}"
                )
                envelope_batch_status_for_digital_cash = (
                    session.query(EnvelopeBatchStatusForDigitalCash)
                    .filter(
                        EnvelopeBatchStatusForDigitalCash.disbursement_envelope_id
                        == disbursement_envelope_id
                    )
                    .with_for_update(nowait=True)
                    .populate_existing()
                    .one()
                )
                _logger.info(f"Lock acquired for envelope {disbursement_envelope_id}")
                _logger.info(
                    f"Total number of disbursements: {len(disbursement_payment_payloads)}"
                )
                # fire the payment
                payment_response = bank_connector.initiate_payment(
                    disbursement_payment_payloads
                )
                _logger.info(
                    f"Payment response for envelope {disbursement_envelope_id} on attempt {attempt}: {payment_response.status}"
                )

                # update envelope status
                if payment_response.status == PaymentStatus.SUCCESS:
                    disbursement_batch_control.sponsor_bank_dispatch_status = (
                        ProcessStatus.PROCESSED.value
                    )
                    disbursement_batch_control.sponsor_bank_dispatch_latest_error_code = (
                        None
                    )
                    disbursement_batch_control.sponsor_bank_dispatch_timestamp = (
                        datetime.now()
                    )
                    disbursement_batch_control.sponsor_bank_dispatch_attempts += 1
                    envelope_batch_status_for_digital_cash.number_of_disbursements_shipped += len(
                        disbursement_payment_payloads
                    )
                else:
                    disbursement_batch_control.sponsor_bank_dispatch_status = (
                        ProcessStatus.PENDING.value
                    )
                    disbursement_batch_control.sponsor_bank_dispatch_latest_error_code = (
                        payment_response.error_code
                    )
                    disbursement_batch_control.sponsor_bank_dispatch_timestamp = (
                        datetime.now()
                    )
                    disbursement_batch_control.sponsor_bank_dispatch_attempts += 1

                session.commit()
                break

            except OperationalError as oe:
                session.rollback()
                _logger.warning(
                    f"Attempt {attempt} to lock envelope {disbursement_envelope_id} failed: {oe}"
                )
                if attempt < max_retries:
                    time.sleep(random.uniform(8, 15))
                else:
                    _logger.error(
                        f"Could not lock after {max_retries} tries, marking pending"
                    )
                    disbursement_batch_control.sponsor_bank_dispatch_status = (
                        ProcessStatus.PENDING.value
                    )
                    disbursement_batch_control.sponsor_bank_dispatch_latest_error_code = (
                        "LockTimeout"
                    )
                    disbursement_batch_control.sponsor_bank_dispatch_timestamp = (
                        datetime.now()
                    )
                    disbursement_batch_control.sponsor_bank_dispatch_attempts += 1
                    session.commit()

            except Exception as e:
                session.rollback()
                _logger.error(
                    f"Unexpected error during disbursement for envelope {disbursement_envelope_id}: {e}"
                )
                disbursement_batch_control.sponsor_bank_dispatch_status = (
                    ProcessStatus.PENDING.value
                )
                disbursement_batch_control.sponsor_bank_dispatch_latest_error_code = (
                    str(e)
                )
                disbursement_batch_control.sponsor_bank_dispatch_timestamp = (
                    datetime.now()
                )
                disbursement_batch_control.sponsor_bank_dispatch_attempts += 1
                if (
                    disbursement_batch_control.sponsor_bank_dispatch_attempts
                    >= _config.max_sponsor_bank_dispatch_attempts
                ):
                    disbursement_batch_control.sponsor_bank_dispatch_status = (
                        ProcessStatus.ERROR.value
                    )
                    _logger.error(
                        f"Max attempts reached for disbursement for envelope {disbursement_envelope_id}"
                    )
                session.commit()
                break

        _logger.info(
            f"Disbursement task for batch {disbursement_batch_control_id} completed"
        )
