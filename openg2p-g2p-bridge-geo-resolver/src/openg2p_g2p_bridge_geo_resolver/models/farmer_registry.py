from datetime import datetime

from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import mapped_column


class G2PFarmerRegistry(BaseORMModel):
    __tablename__ = "g2p_farmer_registry"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    beneficiary_id = mapped_column(String, nullable=True)
    registration_date = mapped_column(DateTime, default=datetime.now(), nullable=False)
    name = mapped_column(String, nullable=False)
    land_area = mapped_column(Float, nullable=True)
    no_of_cattle_heads = mapped_column(Integer, nullable=True)
    no_of_poultry_heads = mapped_column(Integer, nullable=True)
    administrative_zone_id_large = mapped_column(String, nullable=True)
    administrative_zone_mnemonic_large = mapped_column(String, nullable=True)
    administrative_zone_id_small = mapped_column(String, nullable=True)
    administrative_zone_mnemonic_small = mapped_column(String, nullable=True)
