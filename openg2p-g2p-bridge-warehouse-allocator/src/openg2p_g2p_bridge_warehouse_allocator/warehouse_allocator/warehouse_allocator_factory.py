from ..warehouse_allocator.warehouse_allocator_ref_impl import WarehouseAllocatorRefImpl
from ..warehouse_interface.warehouse_allocator_interface import WarehouseAllocator

class WarehouseAllocatorFactory:
    @staticmethod
    def get_warehouse_allocator() -> WarehouseAllocator:
        return WarehouseAllocatorRefImpl() 