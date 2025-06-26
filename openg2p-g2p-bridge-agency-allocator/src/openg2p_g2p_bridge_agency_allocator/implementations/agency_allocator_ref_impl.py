from typing import List, Dict
import random
from ..interface import AgencyAllocator
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
            g2p_agencies = pbms_session.query(G2PAgency).filter(
                G2PAgency.administrative_zone_id_small == geo["administrative_zone_id_small"]
            ).all()
            g2p_agency = random.choice(g2p_agencies)
            if g2p_agency:
                results.append({
                    'batch_control_geo_id': geo['batch_control_geo_id'],
                    'administrative_zone_id_small': geo['administrative_zone_id_small'],
                    'administrative_zone_mnemonic_small': geo['administrative_zone_mnemonic_small'],
                    'benefit_code_id': benefit_code.get('id'),
                    'benefit_code_mnemonic': benefit_code.get('mnemonic'),
                    'program_id': program.get('id'),
                    'program_mnemonic': program.get('mnemonic'),
                    'agency_id': g2p_agency.id,
                    'agency_mnemonic': g2p_agency.mnemonic,
                    'agency_additional_attributes': None,
                })
        return results 