from typing import List, Dict
from ..geo_interface.geo_resolver_interface import GeoResolver

class GeoResolverImpl(GeoResolver):
    def resolve_geo(self, batch_beneficiary_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        # Dummy implementation for demonstration
        results = []
        for item in batch_beneficiary_list:
            results.append({
                "disbursement_batch_control_id": item["disbursement_batch_control_id"],
                "beneficiary_id": item["beneficiary_id"],
                "administrative_area_id_large": "LARGE123",
                "administrative_area_mnemonic_large": "LARGE_MNEMONIC",
                "administrative_area_id_small": "SMALL456",
                "administrative_area_mnemonic_small": "SMALL_MNEMONIC",
            })
        return results 