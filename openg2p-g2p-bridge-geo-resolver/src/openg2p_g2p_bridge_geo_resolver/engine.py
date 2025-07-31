from sqlalchemy import create_engine

from .config import Settings

_config = Settings.get_config()


def get_engine():
    if _config.db_engine_registry:
        db_engine_registry = create_engine(_config.db_engine_registry)
        return {"db_engine_registry": db_engine_registry}
