from typing import List, Dict
from ..warehouse_interface.warehouse_allocator_interface import WarehouseAllocator

class WarehouseAllocatorImpl(WarehouseAllocator):
    def allocate_warehouse(self, batch_control_geo_list: List[Dict]) -> List[Dict]:
        # Dummy implementation: just add dummy warehouse_id and warehouse_mnemonic
        for geo in batch_control_geo_list:
            geo['warehouse_id'] = 'WAREHOUSE123'
            geo['warehouse_mnemonic'] = 'WAREHOUSE_MNEMONIC'
        return batch_control_geo_list 