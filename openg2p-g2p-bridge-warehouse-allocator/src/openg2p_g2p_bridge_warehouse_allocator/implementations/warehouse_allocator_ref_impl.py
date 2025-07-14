import random
from typing import Dict, List

import logging
from sqlalchemy.orm import sessionmaker


from ..interface import WarehouseAllocator
from ..models import G2PWarehouse
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
        benefit_code: Dict,
        program: Dict,
    ) -> List[Dict]:
        results = []
        with session_maker() as pbms_session:
            for geo in large_geo_list:
                g2p_warehouses = (
                    pbms_session.query(G2PWarehouse)
                    .filter(
                        G2PWarehouse.administrative_zone_id_large
                        == geo["administrative_zone_id_large"]
                    )
                    .all()
                )
                g2p_warehouse = random.choice(g2p_warehouses) if g2p_warehouses else None
                if g2p_warehouse:
                    results.append(
                        {
                            "batch_control_geo_id": geo["batch_control_geo_id"],
                            "administrative_zone_id_large": geo[
                                "administrative_zone_id_large"
                            ],
                            "administrative_zone_mnemonic_large": geo[
                                "administrative_zone_mnemonic_large"
                            ],
                            "benefit_code_id": benefit_code.get("id"),
                            "benefit_code_mnemonic": benefit_code.get("mnemonic"),
                            "program_id": program.get("id"),
                            "program_mnemonic": program.get("mnemonic"),
                            "warehouse_id": g2p_warehouse.id,
                            "warehouse_mnemonic": g2p_warehouse.mnemonic,
                            "warehouse_additional_attributes": None,
                            "warehouse_admin_name": g2p_warehouse.admin_name,
                            "warehouse_admin_email": g2p_warehouse.admin_email,
                            "warehouse_admin_phone": g2p_warehouse.contact_phone,
                        }
                    )
        return results
