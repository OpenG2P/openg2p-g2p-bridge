from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..interface.geo_resolver_interface import GeoResolver
from ..models import G2PFarmerRegistry


class GeoResolverImpl(GeoResolver):
    def resolve_geo(
        self, registry_session: Session, batch_beneficiary_list: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        results = []

        beneficiary_ids = [item["beneficiary_id"] for item in batch_beneficiary_list]
        farmer_details = registry_session.execute(
            select(
                G2PFarmerRegistry.beneficiary_id,
                G2PFarmerRegistry.administrative_zone_id_large,
                G2PFarmerRegistry.administrative_zone_mnemonic_large,
                G2PFarmerRegistry.administrative_zone_id_small,
                G2PFarmerRegistry.administrative_zone_mnemonic_small,
            ).where(G2PFarmerRegistry.beneficiary_id.in_(beneficiary_ids))
        ).fetchall()
        farmer_map = {row.beneficiary_id: row for row in farmer_details}
        for item in batch_beneficiary_list:
            row = farmer_map.get(item["beneficiary_id"])
            if row:
                results.append(
                    {
                        "disbursement_id": item["disbursement_id"],
                        "beneficiary_id": item["beneficiary_id"],
                        "administrative_zone_id_large": row.administrative_zone_id_large,
                        "administrative_zone_mnemonic_large": row.administrative_zone_mnemonic_large,
                        "administrative_zone_id_small": row.administrative_zone_id_small,
                        "administrative_zone_mnemonic_small": row.administrative_zone_mnemonic_small,
                    }
                )
        return results
