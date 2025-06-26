from typing import List, Dict
from ..agency_interface.agency_allocator_interface import AgencyAllocator
import random

class AgencyAllocatorRefImpl(AgencyAllocator):
    def allocate_agency(
        self,
        small_geo_list: List[Dict],
        benefit_code: Dict,
        program: Dict
    ) -> List[Dict]:
        # --- STUB: Replace with actual DB query to PBMS Odoo ---
        agencies = [
            {'agency_id': 'AG001', 'agency_mnemonic': 'Agency_A', 'agency_additional_attributes': 'Govt'},
            {'agency_id': 'AG002', 'agency_mnemonic': 'Agency_B', 'agency_additional_attributes': 'NGO'},
            {'agency_id': 'AG003', 'agency_mnemonic': 'Agency_C', 'agency_additional_attributes': 'Private'},
        ]
        # ------------------------------------------------------

        results = []
        for geo in small_geo_list:
            agency = random.choice(agencies)
            results.append({
                'batch_control_geo_id': geo['batch_control_geo_id'],
                'administrative_zone_id_small': geo['administrative_zone_id_small'],
                'administrative_zone_mnemonic_small': geo['administrative_zone_mnemonic_small'],
                'benefit_code_id': benefit_code.get('id'),
                'benefit_code_mnemonic': benefit_code.get('mnemonic'),
                'program_id': program.get('id'),
                'program_mnemonic': program.get('mnemonic'),
                'agency_id': agency['agency_id'],
                'agency_mnemonic': agency['agency_mnemonic'],
                'agency_additional_attributes': agency['agency_additional_attributes'],
            })
        return results 