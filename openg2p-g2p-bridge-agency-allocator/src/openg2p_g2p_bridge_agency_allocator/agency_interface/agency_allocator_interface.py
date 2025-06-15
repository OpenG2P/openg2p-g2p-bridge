from abc import ABC, abstractmethod
from typing import List, Dict

class AgencyAllocator(ABC):
    @abstractmethod
    def allocate_agency(self, batch_control_geo_list: List[Dict]) -> List[Dict]:
        """
        Accepts a list of disbursement_batch_control_geo dicts.
        Returns a list of dicts with agency_id and agency_mnemonic populated.
        """
        pass 