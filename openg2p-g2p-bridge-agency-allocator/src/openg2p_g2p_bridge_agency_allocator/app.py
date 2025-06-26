# ruff: noqa: E402


from openg2p_fastapi_common.app import Initializer as BaseInitializer
from .agency_allocator import AgencyAllocatorFactory, ExampleAgencyAllocator


class Initializer(BaseInitializer):
    def initialize(self, **kwargs):
        AgencyAllocatorFactory()
        ExampleAgencyAllocator()
