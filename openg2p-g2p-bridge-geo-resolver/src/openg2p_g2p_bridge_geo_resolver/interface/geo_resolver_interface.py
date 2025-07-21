from abc import ABC, abstractmethod
from typing import Dict, List


class GeoResolver(ABC):
    @abstractmethod
    def resolve_geo(
        self, batch_beneficiary_list: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Receives a list of dicts with keys: disbursement_id, beneficiary_id
        Returns a list of dicts with keys: disbursement_id, beneficiary_id, administrative_zone_id_large, administrative_zone_mnemonic_large, administrative_zone_id_small, administrative_zone_mnemonic_small
        """
        pass
