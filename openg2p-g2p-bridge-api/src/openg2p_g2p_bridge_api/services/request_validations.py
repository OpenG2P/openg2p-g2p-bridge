from openg2p_fastapi_common.service import BaseService
from openg2p_g2p_bridge_models.errors.exceptions import RequestValidationException
from openg2p_g2pconnect_common_lib.schemas import SyncResponseStatusReasonCodeEnum

from fastapi import UploadFile

from ..config import Settings

_config = Settings.get_config()


class RequestValidation(BaseService):
    def validate_signature(self, is_signature_valid) -> None:
        if not is_signature_valid:
            raise RequestValidationException(
                code=SyncResponseStatusReasonCodeEnum.rjct_jwt_invalid,
                message=SyncResponseStatusReasonCodeEnum.rjct_jwt_invalid,
            )

        return None

    def validate_create_disbursement_envelope_request_header(self, request) -> None:
        if request.header.action != "create_disbursement_envelope":
            raise RequestValidationException(
                code=SyncResponseStatusReasonCodeEnum.rjct_action_not_supported,
                message=SyncResponseStatusReasonCodeEnum.rjct_action_not_supported,
            )
        return None

    def validate_cancel_disbursement_envelope_request_header(self, request) -> None:
        if request.header.action != "cancel_disbursement_envelope":
            raise RequestValidationException(
                code=SyncResponseStatusReasonCodeEnum.rjct_action_not_supported,
                message=SyncResponseStatusReasonCodeEnum.rjct_action_not_supported,
            )
        return None

    def validate_request(self, request) -> None:
        return None

    def validate_mt940_file(self, request: UploadFile) -> None:
        # Validate file size: get file size by seeking to the end.
        request.file.seek(0, 2)
        file_size = request.file.tell()
        request.file.seek(0)

        if file_size > _config.max_upload_file_size:
            raise RequestValidationException(
                code=SyncResponseStatusReasonCodeEnum.rjct_file_size_exceeded,
                message=SyncResponseStatusReasonCodeEnum.rjct_file_size_exceeded,
            )
        # Validate file type using the content_type attribute
        if request.content_type not in _config.supported_file_types:
            raise RequestValidationException(
                code=SyncResponseStatusReasonCodeEnum.rjct_file_type_not_supported,
                message=SyncResponseStatusReasonCodeEnum.rjct_file_type_not_supported,
            )

        return None
