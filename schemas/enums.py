import enum


class OrderSource(str, enum.Enum):
    UDS = "UDS"
    MESSENGER = "MESSENGER"
    TABLE = "TABLE"


class OrderStatus(str, enum.Enum):
    NEW = "NEW"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
