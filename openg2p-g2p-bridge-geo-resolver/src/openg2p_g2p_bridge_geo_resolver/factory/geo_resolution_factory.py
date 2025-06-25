from ..implementations import GeoResolverImpl
from ..interface import GeoResolver

class GeoResolutionFactory:
    @staticmethod
    def get_geo_resolver() -> GeoResolver:
        return GeoResolverImpl() 