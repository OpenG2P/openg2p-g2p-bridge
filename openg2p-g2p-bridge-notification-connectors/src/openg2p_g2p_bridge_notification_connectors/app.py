# ruff: noqa: E402

from .config import Settings

from openg2p_fastapi_common.app import Initializer as BaseInitializer

from .factory import NotificationFactory
from .implementations import NovuNotifier


class Initializer(BaseInitializer):
    def initialize(self, **kwargs):
        NotificationFactory()
        NovuNotifier()
