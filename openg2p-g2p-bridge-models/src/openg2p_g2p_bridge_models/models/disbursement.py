from datetime import datetime
from enum import Enum

from openg2p_fastapi_common.models import BaseORMModelWithTimes
from sqlalchemy import UUID, DateTime, Float, Integer, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from .common_enums import ProcessStatus


class DisbursementCancellationStatus(Enum):
    NOT_CANCELLED = "NOT_CANCELLED"
    CANCELLED = "CANCELLED"


class MapperResolvedFaType(Enum):
    BANK_ACCOUNT = "BANK_ACCOUNT"
    MOBILE_WALLET = "MOBILE_WALLET"
    EMAIL_WALLET = "EMAIL_WALLET"


class Disbursement(BaseORMModelWithTimes):
    __tablename__ = "disbursements"
    disbursement_id: Mapped[str] = mapped_column(String, unique=True)
    mis_reference_number: Mapped[str] = mapped_column(
        String, nullable=True, default=None
    )
    disbursement_envelope_id: Mapped[str] = mapped_column(String, index=True)
    beneficiary_id: Mapped[str] = mapped_column(String)
    beneficiary_name: Mapped[str] = mapped_column(String)
    disbursement_amount: Mapped[float] = mapped_column(Float)
    narrative: Mapped[str] = mapped_column(String)
    receipt_time_stamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    cancellation_status: Mapped[DisbursementCancellationStatus] = mapped_column(
        SqlEnum(DisbursementCancellationStatus),
        default=DisbursementCancellationStatus.NOT_CANCELLED,
    )
    cancellation_time_stamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=None
    )
    disbursement_cycle_id: Mapped[str] = mapped_column(UUID)
    disbursement_batch_control_id: Mapped[str] = mapped_column(UUID)


class DisbursementBatchControl(BaseORMModelWithTimes):
    __tablename__ = "disbursement_batch_control"
    disbursement_batch_control_id: Mapped[str] = mapped_column(UUID, unique=True, index=True)
    disbursement_cycle_id: Mapped[str] = mapped_column(UUID, index=True)
    disbursement_envelope_id: Mapped[str] = mapped_column(UUID, index=True)
    fa_resolution_status: Mapped[ProcessStatus] = mapped_column(SqlEnum(ProcessStatus))
    fa_resolution_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    fa_resolution_latest_error_code: Mapped[str] = mapped_column(String, nullable=True, default=None)
    fa_resolution_attempts: Mapped[int] = mapped_column(Integer, default=0)
    sponsor_bank_dispatch_status: Mapped[ProcessStatus] = mapped_column(SqlEnum(ProcessStatus))
    sponsor_bank_dispatch_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    sponsor_bank_dispatch_latest_error_code: Mapped[str] = mapped_column(String, nullable=True, default=None)
    sponsor_bank_dispatch_attempts: Mapped[int] = mapped_column(Integer, default=0)
    geo_resolutuon_status: Mapped[ProcessStatus] = mapped_column(SqlEnum(ProcessStatus))
    geo_resolution_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    geo_resolution_latest_error_code: Mapped[str] = mapped_column(String, nullable=True, default=None)
    geo_resolution_attempts: Mapped[int] = mapped_column(Integer, default=0)
    warehouse_allocation_status: Mapped[ProcessStatus] = mapped_column(SqlEnum(ProcessStatus))
    warehouse_allocation_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    warehouse_allocation_latest_error_code: Mapped[str] = mapped_column(String, nullable=True, default=None)
    warehouse_allocation_attempts: Mapped[int] = mapped_column(Integer, default=0)


class DisbursementResolutionFinancialAddress(BaseORMModelWithTimes):
    __tablename__ = "disbursement_resolution_financial_address"
    disbursement_batch_control_id = mapped_column(UUID, nullable=True, default=None, index=True)
    disbursement_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    beneficiary_id: Mapped[str] = mapped_column(String, index=True)
    mapper_resolved_fa: Mapped[str] = mapped_column(String, nullable=True, default=None)
    mapper_resolved_name: Mapped[str] = mapped_column(
        String, nullable=True, default=None
    )
    mapper_resolved_fa_type: Mapped[MapperResolvedFaType] = mapped_column(
        SqlEnum(MapperResolvedFaType), nullable=True, default=None
    )
    bank_account_number: Mapped[str] = mapped_column(
        String, nullable=True, default=None
    )
    bank_code: Mapped[str] = mapped_column(String, nullable=True, default=None)
    branch_code: Mapped[str] = mapped_column(String, nullable=True, default=None)
    mobile_number: Mapped[str] = mapped_column(String, nullable=True, default=None)
    mobile_wallet_provider: Mapped[str] = mapped_column(
        String, nullable=True, default=None
    )
    email_address: Mapped[str] = mapped_column(String, nullable=True, default=None)
    email_wallet_provider: Mapped[str] = mapped_column(
        String, nullable=True, default=None
    )
