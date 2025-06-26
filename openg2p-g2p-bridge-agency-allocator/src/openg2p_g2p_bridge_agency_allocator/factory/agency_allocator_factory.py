from ..implementations import AgencyAllocatorRefImpl
from ..interface import AgencyAllocator

class AgencyAllocatorFactory:
    @staticmethod
    def get_agency_allocator() -> AgencyAllocator:
        return AgencyAllocatorRefImpl() 