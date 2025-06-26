from ..agency_allocator.agency_allocator_ref_impl import AgencyAllocatorRefImpl
from ..agency_interface.agency_allocator_interface import AgencyAllocator

class AgencyAllocatorFactory:
    @staticmethod
    def get_agency_allocator() -> AgencyAllocator:
        return AgencyAllocatorRefImpl() 