import random
from typing import Dict, List
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

from ..interface import AgencyAllocator
from ..models import G2PAgency
from ..config import Settings
from ..app import get_engine


_logger = logging.getLogger("agency_allocator_ref_impl")
_engine = get_engine()
_config = Settings.get_config()
session_maker = sessionmaker(
    bind=_engine.get("db_engine_pbms"), expire_on_commit=False
)

class AgencyAllocatorRefImpl(AgencyAllocator):
    def allocate_agency(
        self,
        small_geo_list: List[Dict],
        benefit_code: Dict,
        program: Dict,
    ) -> List[Dict]:

        results = []
        with session_maker() as pbms_session:
            # Fetch G2P agencies based on the small geo list
            for geo in small_geo_list:
                g2p_agencies = (
                    pbms_session.query(G2PAgency)
                    .filter(
                        G2PAgency.administrative_zone_id_small
                        == geo["administrative_zone_id_small"]
                    )
                    .all()
                )
                g2p_agency = random.choice(g2p_agencies) if g2p_agencies else None
                if g2p_agency:
                    results.append(
                        {
                            "batch_control_geo_id": geo["batch_control_geo_id"],
                            "administrative_zone_id_small": geo[
                                "administrative_zone_id_small"
                            ],
                            "administrative_zone_mnemonic_small": geo[
                                "administrative_zone_mnemonic_small"
                            ],
                            "benefit_code_id": benefit_code.get("id"),
                            "benefit_code_mnemonic": benefit_code.get("mnemonic"),
                            "program_id": program.get("id"),
                            "program_mnemonic": program.get("mnemonic"),
                            "agency_id": g2p_agency.id,
                            "agency_mnemonic": g2p_agency.mnemonic,
                            "agency_additional_attributes": None,
                        }
                    )
        return results
