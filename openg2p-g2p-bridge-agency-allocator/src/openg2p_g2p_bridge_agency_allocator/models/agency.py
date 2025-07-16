from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy import Integer, String
from sqlalchemy.orm import mapped_column


class G2PAgency(BaseORMModel):
    __tablename__ = "g2p_agencies"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    mnemonic = mapped_column(String, nullable=True)
    administrative_zone_id_small = mapped_column(String, nullable=True)
    administrative_zone_mnemonic_small = mapped_column(String, nullable=True)
