# ruff: noqa: E402
import logging

from openg2p_fastapi_common.app import Initializer as BaseInitializer
from openg2p_fastapi_auth.auth.factory import AuthFactory
from openg2p_fastapi_auth.auth.implementations import BeneficiaryEsignetAuth

from .config import Settings
from .controllers import DisbursementController
from .services import DisbursementService

_config = Settings.get_config()
_logger = logging.getLogger(_config.logging_default_logger_name)


class Initializer(BaseInitializer):
    def initialize(self, **kwargs):
        super().initialize()

        AuthFactory()
        BeneficiaryEsignetAuth()
        DisbursementService()
        DisbursementController().post_init()
