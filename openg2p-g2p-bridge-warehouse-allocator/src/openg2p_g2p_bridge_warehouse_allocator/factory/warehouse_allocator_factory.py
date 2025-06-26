from ..implementations import WarehouseAllocatorRefImpl
from ..interface import WarehouseAllocator


class WarehouseAllocatorFactory:
    @staticmethod
    def get_warehouse_allocator() -> WarehouseAllocator:
        return WarehouseAllocatorRefImpl()
