from openg2p_fastapi_common.service import BaseService

from ..implementations import FarmerGeoResolverImpl
from ..interface import GeoResolver


class GeoResolutionFactory(BaseService):
    @staticmethod
    def get_geo_resolver(target_registry: str) -> GeoResolver:
        if target_registry.lower() == "farmer":
            return FarmerGeoResolverImpl()
        return None
