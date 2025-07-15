from typing import Dict, List
import logging


from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from ..interface.geo_resolver_interface import GeoResolver
from ..models import G2PFarmerRegistry
from ..engine import get_engine

_logger = logging.getLogger("farmer_geo_resolver_impl")
_engine = get_engine()

session_maker = sessionmaker(
    bind=_engine.get("db_engine_farmer"), expire_on_commit=False
)

class FarmerGeoResolverImpl(GeoResolver):
    def resolve_geo(
        self,  batch_beneficiary_list: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        with session_maker() as registry_session:
            _logger.info(
                f"Resolving geo for {len(batch_beneficiary_list)} beneficiaries"
            )
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
