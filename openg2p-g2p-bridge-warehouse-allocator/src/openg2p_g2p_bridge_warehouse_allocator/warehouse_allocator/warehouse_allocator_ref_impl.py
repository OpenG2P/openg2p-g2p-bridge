from typing import List, Dict
from ..warehouse_interface.warehouse_allocator_interface import WarehouseAllocator
import random

class WarehouseAllocatorRefImpl(WarehouseAllocator):
    def allocate_warehouse(
        self,
        large_geo_list: List[Dict],
        benefit_code: Dict,
        program: Dict
    ) -> List[Dict]:
        # --- STUB: Replace with actual DB query to PBMS Odoo ---
        warehouses = [
            {'id': 'WH001', 'warehouse_mnemonic': 'Warehouse_A', 'warehouse_additional_attributes': 'additional_attr'},
            {'id': 'WH002', 'warehouse_mnemonic': 'Warehouse_B', 'warehouse_additional_attributes': 'additional_attr'},
            {'id': 'WH003', 'warehouse_mnemonic': 'Warehouse_C', 'warehouse_additional_attributes': 'additional_attr'},
        ]
        # ------------------------------------------------------

        results = []
        for geo in large_geo_list:
            warehouse = random.choice(warehouses)
            results.append({
                'batch_control_geo_id': geo['batch_control_geo_id'],
                'administrative_zone_id_large': geo['administrative_zone_id_large'],
                'administrative_zone_mnemonic_large': geo['administrative_zone_mnemonic_large'],
                'benefit_code_id': benefit_code.get('id'),
                'benefit_code_mnemonic': benefit_code.get('mnemonic'),
                'program_id': program.get('id'),
                'program_mnemonic': program.get('mnemonic'),
                'warehouse_id': warehouse['id'],
                'warehouse_mnemonic': warehouse['warehouse_mnemonic'],
                'warehouse_additional_attributes': warehouse['warehouse_additional_attributes'],
            })
        return results 