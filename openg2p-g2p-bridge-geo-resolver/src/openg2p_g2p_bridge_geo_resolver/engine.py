from sqlalchemy import create_engine
from .config import Settings

_config = Settings.get_config()

def get_engine():
    if _config.db_datasource_pbms:
        db_engine_farmer = create_engine(_config.db_engine_farmer)
        return {"db_engine_farmer": db_engine_farmer} 