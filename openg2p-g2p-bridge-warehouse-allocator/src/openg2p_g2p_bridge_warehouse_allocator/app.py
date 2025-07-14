# ruff: noqa: E402

from .config import Settings

_config = Settings.get_config()

from openg2p_fastapi_common.app import Initializer as BaseInitializer

from .factory import WarehouseAllocatorFactory
from .implementations import WarehouseAllocatorRefImpl
from sqlalchemy import create_engine


def get_engine():
    if _config.db_datasource_pbms:
        db_engine_pbms = create_engine(_config.db_datasource_pbms)
        return {"db_engine_pbms": db_engine_pbms}


class Initializer(BaseInitializer):
    def initialize(self, **kwargs):
        WarehouseAllocatorFactory()
        WarehouseAllocatorRefImpl()
