from typing import List, Dict
from ..warehouse_interface.warehouse_allocator_interface import WarehouseAllocator
from sqlalchemy.orm import Session
from ..models import G2PWarehouse

class WarehouseAllocatorRefImpl(WarehouseAllocator):
    def allocate_warehouse(
        self,
        pbms_session: Session,
        large_geo_list: List[Dict],
        benefit_code: Dict,
        program: Dict
    ) -> List[Dict]:
        results = []
        for geo in large_geo_list:
            warehouse = pbms_session.query(G2PWarehouse).filter(
                G2PWarehouse.administrative_zone_id_large == geo["administrative_zone_id_large"]
            ).first()
            if warehouse:
                results.append({
                    'batch_control_geo_id': geo['batch_control_geo_id'],
                    'administrative_zone_id_large': geo['administrative_zone_id_large'],
                    'administrative_zone_mnemonic_large': geo['administrative_zone_mnemonic_large'],
                    'benefit_code_id': benefit_code.get('id'),
                    'benefit_code_mnemonic': benefit_code.get('mnemonic'),
                    'program_id': program.get('id'),
                    'program_mnemonic': program.get('mnemonic'),
                    'warehouse_id': warehouse.id,
                    'warehouse_mnemonic': warehouse.mnemonic,
                    'warehouse_additional_attributes': None,
                })
        return results 