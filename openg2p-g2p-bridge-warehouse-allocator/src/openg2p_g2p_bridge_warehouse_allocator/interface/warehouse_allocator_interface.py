from abc import ABC, abstractmethod
from typing import Dict, List

from sqlalchemy.orm import Session


class WarehouseAllocator(ABC):
    @abstractmethod
    def allocate_warehouse(
        self,
        pbms_session: Session,
        large_geo_list: List[Dict],
        benefit_code: Dict,
        program: Dict,
    ) -> List[Dict]:
        """
        Accepts:
          - pbms_session: SQLAlchemy Session for PBMS DB
          - large_geo_list: List of dicts, each with batch_control_geo_id, large_geo_ID, large_geo_Mnemonic
          - benefit_code: Dict with id and mnemonic
          - program: Dict with id and mnemonic
        Returns a list of dicts with warehouse allocation info for each geo.
        """
        pass
