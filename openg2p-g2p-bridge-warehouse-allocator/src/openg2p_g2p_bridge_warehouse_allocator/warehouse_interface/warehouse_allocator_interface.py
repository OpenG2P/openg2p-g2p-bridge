from abc import ABC, abstractmethod
from typing import List, Dict

class WarehouseAllocator(ABC):
    @abstractmethod
    def allocate_warehouse(self, batch_control_geo_list: List[Dict]) -> List[Dict]:
        """
        Accepts a list of disbursement_batch_control_geo dicts.
        Returns a list of dicts with warehouse_id and warehouse_mnemonic populated.
        """
        pass 