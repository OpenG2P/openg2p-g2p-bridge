from sqlalchemy import create_engine

from .config import Settings

_config = Settings.get_config()


def get_engine():
    if _config.db_datasource:
        db_engine_bridge = create_engine(_config.db_datasource)
        db_engine_pbms = create_engine(_config.db_datasource_pbms_db)
        return {
            "db_engine_bridge": db_engine_bridge,
            "db_engine_pbms": db_engine_pbms,
        }
