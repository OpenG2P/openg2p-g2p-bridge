from typing import List, Dict
from ..agency_interface.agency_allocator_interface import AgencyAllocator

class AgencyAllocatorImpl(AgencyAllocator):
    def allocate_agency(self, batch_control_geo_list: List[Dict]) -> List[Dict]:
        # Dummy implementation: just add dummy agency_id and agency_mnemonic
        for geo in batch_control_geo_list:
            geo['agency_id'] = 'AGENCY123'
            geo['agency_mnemonic'] = 'AGENCY_MNEMONIC'
        return batch_control_geo_list 