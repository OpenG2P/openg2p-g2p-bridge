import random
from typing import Dict, List

import logging
from sqlalchemy.orm import sessionmaker


from ..interface import WarehouseAllocator
from ..models import G2PWarehouse, G2PWarehouseProgramBenefitCode, G2PAdministrativeAreaLargeWarehouseRel
from ..engine import get_engine

_logger = logging.getLogger("warehouse_allocator_ref_impl")
_engine = get_engine()
session_maker = sessionmaker(
    bind=_engine.get("db_engine_pbms"), expire_on_commit=False
)

class WarehouseAllocatorRefImpl(WarehouseAllocator):
    def allocate_warehouse(
        self,
        large_geo_list: List[Dict],
        benefit_code_id: str,
        program_id: str,
    ) -> List[Dict]:
        results = []
        with session_maker() as pbms_session:
            for geo in large_geo_list:
                # 1. Get warehouse_ids with program_id and benefit_code_id
                program_benefit_warehouse_ids = set([
                    row.warehouse_id for row in pbms_session.query(G2PWarehouseProgramBenefitCode)
                    .filter(
                        G2PWarehouseProgramBenefitCode.program_id == program_id,
                        G2PWarehouseProgramBenefitCode.benefit_code_id == benefit_code_id
                    ).all()
                ])
                # 2. Get warehouse_ids under geo["administrative_zone_id_large"]
                geo_warehouse_ids = set([
                    row.g2p_warehouse_id for row in pbms_session.query(G2PAdministrativeAreaLargeWarehouseRel)
                    .filter(
                        G2PAdministrativeAreaLargeWarehouseRel.g2p_administrative_area_large_id == geo["administrative_zone_id_large"]
                    ).all()
                ])
                # 3. Intersect both sets
                warehouse_ids = list(program_benefit_warehouse_ids & geo_warehouse_ids)
                g2p_warehouses = (
                    pbms_session.query(G2PWarehouse)
                    .filter(G2PWarehouse.id.in_(warehouse_ids))
                    .all()
                )
                g2p_warehouse = random.choice(g2p_warehouses) if g2p_warehouses else None
                warehouse_additional_attributes = None
                if g2p_warehouse:
                    # Try to get the additional_info from G2PWarehouseProgramBenefitCode for this warehouse
                    benefit_code_entry = pbms_session.query(G2PWarehouseProgramBenefitCode).filter(
                        G2PWarehouseProgramBenefitCode.warehouse_id == g2p_warehouse.id,
                        G2PWarehouseProgramBenefitCode.program_id == program_id,
                        G2PWarehouseProgramBenefitCode.benefit_code_id == benefit_code_id
                    ).first()
                    warehouse_additional_attributes = benefit_code_entry.additional_info if benefit_code_entry else None
                    results.append(
                        {
                            "batch_control_geo_id": geo["batch_control_geo_id"],
                            "administrative_zone_id_large": geo["administrative_zone_id_large"],
                            "administrative_zone_mnemonic_large": geo["administrative_zone_mnemonic_large"],
                            "benefit_code_id": benefit_code_id,
                            "program_id": program_id,
                            "warehouse_id": g2p_warehouse.id,
                            "warehouse_mnemonic": g2p_warehouse.warehouse_mnemonic,
                            "warehouse_name": g2p_warehouse.name,
                            "warehouse_admin_name": g2p_warehouse.admin_name,
                            "warehouse_admin_email": g2p_warehouse.admin_email,
                            "warehouse_admin_phone": g2p_warehouse.admin_mobile,
                            "warehouse_additional_attributes": warehouse_additional_attributes,
                        }
                    )
        return results
