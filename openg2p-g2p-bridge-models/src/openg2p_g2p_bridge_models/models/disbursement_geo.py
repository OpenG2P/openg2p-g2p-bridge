from openg2p_fastapi_common.models import BaseORMModelWithTimes
from sqlalchemy import UUID, Integer, String, Float
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column
from .common_enums import ProcessStatus

class DisbursementBatchControlGeo(BaseORMModelWithTimes):
    __tablename__ = "disbursement_batch_control_geo"
    disbursement_control_geo_id: Mapped[str] = mapped_column(UUID, unique=True)
    disbursement_cycle_id: Mapped[str] = mapped_column(UUID)
    disbursement_envelope_id: Mapped[str] = mapped_column(UUID)
    disbursement_batch_control_id: Mapped[str] = mapped_column(UUID)
    administrative_zone_id_large: Mapped[str] = mapped_column(String)
    administrative_zone_mnemonic_large: Mapped[str] = mapped_column(String)
    administrative_zone_small: Mapped[str] = mapped_column(String)
    administrative_zone_mnemonic_small: Mapped[str] = mapped_column(String)
    total_quantity: Mapped[float] = mapped_column(Float)
    warehouse_id: Mapped[str] = mapped_column(UUID)
    warehouse_mnemonic: Mapped[str] = mapped_column(String)
    agency_id: Mapped[str] = mapped_column(UUID)
    agency_mnemonic: Mapped[str] = mapped_column(String)
    warehouse_notification_status: Mapped[ProcessStatus] = mapped_column(SqlEnum(ProcessStatus))
    agency_notification_status: Mapped[ProcessStatus] = mapped_column(SqlEnum(ProcessStatus))
    __table_args__ = (
        # Unique index on (disbursement_batch_control_id, administrative_zone_id_large, administrative_zone_small)
        {"sqlite_autoincrement": True},
    )

class DisbursementResolutionGeoAddress(BaseORMModelWithTimes):
    __tablename__ = "disbursement_resolution_geo_address"
    disbursement_id: Mapped[str] = mapped_column(UUID, unique=True)
    disbursement_cycle_id: Mapped[str] = mapped_column(UUID, index=True)
    disbursement_envelope_id: Mapped[str] = mapped_column(UUID, index=True)
    disbursement_batch_control_id: Mapped[str] = mapped_column(UUID, index=True)
    beneficiary_id: Mapped[str] = mapped_column(String, index=True)
    administrative_zone_large: Mapped[str] = mapped_column(String)
    administrative_zone_small: Mapped[str] = mapped_column(String)
    warehouse_id: Mapped[str] = mapped_column(UUID, index=True)
    warehouse_mnemonic: Mapped[str] = mapped_column(String)
    agency_id: Mapped[str] = mapped_column(UUID, index=True)
    agency_mnemonic: Mapped[str] = mapped_column(String)
    beneficiary_notification_status: Mapped[ProcessStatus] = mapped_column(SqlEnum(ProcessStatus)) 