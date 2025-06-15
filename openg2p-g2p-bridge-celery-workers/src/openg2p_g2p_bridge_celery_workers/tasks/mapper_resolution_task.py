import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import asyncio

from openg2p_g2p_bridge_models.models import (
    DisbursementBatchControl,
    DisbursementResolutionFinancialAddress,
    ProcessStatus,
    Disbursement,
)
from ..helpers import ResolveHelper
from openg2p_g2pconnect_mapper_lib.client import MapperResolveClient
from openg2p_g2pconnect_mapper_lib.schemas import ResolveRequest

from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker
from ..app import celery_app, get_engine
from ..config import Settings


# Configure logging
_config = Settings.get_config()
_logger = logging.getLogger(_config.logging_default_logger_name)
_engine = get_engine()


@celery_app.task(name="mapper_resolution_worker")
def mapper_resolution_worker(disbursement_batch_control_id: str):
    _logger.info(f"Resolving the batch: {disbursement_batch_control_id}")
    session_maker = sessionmaker(bind=_engine, expire_on_commit=False)

    with session_maker() as session:
        batch_control = session.execute(
            select(DisbursementBatchControl).filter(
                DisbursementBatchControl.disbursement_batch_control_id == disbursement_batch_control_id
            )
        ).scalars().first()
        if not batch_control:
            _logger.error(f"No DisbursementBatchControl found for id {disbursement_batch_control_id}")
            return

        disbursements = session.execute(
            select(Disbursement).filter(
                Disbursement.disbursement_batch_control_id == disbursement_batch_control_id
            )
        ).scalars().all()
        _logger.info(f"Found {len(disbursements)} disbursements for batch control {disbursement_batch_control_id}")

        beneficiary_disbursement_map = {
            d.beneficiary_id: d.disbursement_id for d in disbursements
        }
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resolve_response, error_msg = loop.run_until_complete(
                make_resolve_request(disbursements)
            )
        finally:
            loop.close()

        if not resolve_response:
            _logger.error(
                f"Failed to resolve the request for batch {disbursement_batch_control_id}: {error_msg}"
            )
            session.query(DisbursementBatchControl).filter(
                DisbursementBatchControl.disbursement_batch_control_id == disbursement_batch_control_id
            ).update(
                {
                    DisbursementBatchControl.fa_resolution_status: ProcessStatus.PENDING,
                    DisbursementBatchControl.fa_resolution_latest_error_code: error_msg,
                    DisbursementBatchControl.fa_resolution_attempts: DisbursementBatchControl.fa_resolution_attempts + 1,
                }
            )
            session.commit()
            return

        process_and_store_resolution(
            disbursement_batch_control_id,
            resolve_response,
            beneficiary_disbursement_map,
            session,
        )


async def make_resolve_request(disbursements):
    _logger.info("Making resolve request")
    resolve_helper = ResolveHelper.get_component()

    single_resolve_requests = [
        resolve_helper.construct_single_resolve_request(d.beneficiary_id)
        for d in disbursements
    ]
    resolve_request: ResolveRequest = resolve_helper.construct_resolve_request(
        single_resolve_requests
    )
    jwt_token = await resolve_helper.create_jwt_token(
        resolve_request.model_dump(mode="json")
    )
    headers = {"content-type": "application/json", "Signature": jwt_token}

    resolve_client = MapperResolveClient()
    try:
        resolve_response = await resolve_client.resolve_request(
            resolve_request, headers, _config.mapper_resolve_api_url
        )
        return resolve_response, None
    except Exception as e:
        _logger.error(f"Failed to resolve the request: {e}")
        error_msg = f"Failed to resolve the request: {e}"
        return None, error_msg


def process_and_store_resolution(
    disbursement_batch_control_id,
    resolve_response,
    beneficiary_disbursement_map,
    session,
):
    _logger.info("Processing and storing resolution")
    resolve_helper = ResolveHelper.get_component()
    details_list = []
    batch_has_error = False
    for single_response in resolve_response.message.resolve_response:
        _logger.info(
            f"Processing the response for beneficiary: {single_response.id}"
        )
        disbursement_id = beneficiary_disbursement_map.get(single_response.id)
        if disbursement_id and single_response.fa:
            _logger.info(
                f"Resolved the request for beneficiary: {single_response.id}"
            )
            deconstructed_fa = resolve_helper.deconstruct_fa(single_response.fa)
            details = DisbursementResolutionFinancialAddress(
                disbursement_batch_control_id=disbursement_batch_control_id,
                disbursement_id=disbursement_id,
                beneficiary_id=single_response.id,
                mapper_resolved_fa=single_response.fa,
                mapper_resolved_name=single_response.account_provider_info.name
                if single_response.account_provider_info
                else None,
                **deconstructed_fa,
            )
            details_list.append(details)
        else:
            _logger.error(
                f"Failed to resolve the request for beneficiary: {single_response.id}"
            )
            batch_has_error = True

    session.add_all(details_list)
    if not batch_has_error:
        _logger.info("Batch has no error")
        session.query(DisbursementBatchControl).filter(
            DisbursementBatchControl.disbursement_batch_control_id
            == disbursement_batch_control_id
        ).update(
            {
                DisbursementBatchControl.fa_resolution_status: ProcessStatus.PROCESSED,
                DisbursementBatchControl.fa_resolution_timestamp: datetime.now(),
                DisbursementBatchControl.fa_resolution_latest_error_code: None,
                DisbursementBatchControl.fa_resolution_attempts: DisbursementBatchControl.fa_resolution_attempts + 1,
            }
        )
    else:
        _logger.info("Batch has error")
        session.query(DisbursementBatchControl).filter(
            DisbursementBatchControl.disbursement_batch_control_id
            == disbursement_batch_control_id
        ).update(
            {
                DisbursementBatchControl.fa_resolution_status: ProcessStatus.PENDING,
                DisbursementBatchControl.fa_resolution_latest_error_code: "Failed to resolve the request for a beneficiary id",
                DisbursementBatchControl.fa_resolution_attempts: DisbursementBatchControl.fa_resolution_attempts + 1,
            }
        )
    _logger.info("Stored the resolution")
    session.flush()
    session.commit()
