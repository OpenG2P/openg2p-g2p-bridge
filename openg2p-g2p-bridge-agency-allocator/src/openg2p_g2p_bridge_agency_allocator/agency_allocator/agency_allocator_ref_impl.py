from typing import List, Dict
from ..agency_interface.agency_allocator_interface import AgencyAllocator
from sqlalchemy.orm import Session
from openg2p_g2p_bridge_models.models.disbursement_geo import DisbursementBatchControlGeo
from ..models import G2PAgency

class AgencyAllocatorRefImpl(AgencyAllocator):
    def allocate_agency(
        self,
        pbms_session: Session,
        small_geo_list: List[Dict],
        benefit_code: Dict,
        program: Dict
    ) -> List[Dict]:
        results = []
        for geo in small_geo_list:
            agency = pbms_session.query(G2PAgency).filter(
                G2PAgency.administrative_zone_id_small == geo["administrative_zone_id_small"]
            ).first()
            if agency:
                results.append({
                    'batch_control_geo_id': geo['batch_control_geo_id'],
                    'administrative_zone_id_small': geo['administrative_zone_id_small'],
                    'administrative_zone_mnemonic_small': geo['administrative_zone_mnemonic_small'],
                    'benefit_code_id': benefit_code.get('id'),
                    'benefit_code_mnemonic': benefit_code.get('mnemonic'),
                    'program_id': program.get('id'),
                    'program_mnemonic': program.get('mnemonic'),
                    'agency_id': agency.id,
                    'agency_mnemonic': agency.mnemonic,
                    'agency_additional_attributes': None,
                })
        return results 