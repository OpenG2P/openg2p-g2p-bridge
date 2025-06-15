from abc import ABC, abstractmethod
from typing import List, Dict

class GeoResolver(ABC):
    @abstractmethod
    def resolve_geo(self, batch_beneficiary_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Receives a list of dicts with keys: disbursement_batch_control_id, beneficiary_id
        Returns a list of dicts with keys: disbursement_batch_control_id, beneficiary_id, administrative_area_id_large, administrative_area_mnemonic_large, administrative_area_id_small, administrative_area_mnemonic_small
        """
        pass 