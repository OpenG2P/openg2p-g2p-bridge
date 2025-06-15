from ..geo_resolver.geo_resolver_impl import GeoResolverImpl
from ..geo_interface.geo_resolver_interface import GeoResolver

class GeoResolutionFactory:
    @staticmethod
    def get_geo_resolver() -> GeoResolver:
        return GeoResolverImpl() 