import os
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from pynamodb.attributes import (
    BooleanAttribute,
    ListAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.indexes import AllProjection, GlobalSecondaryIndex
from pynamodb.models import Model


class RestaurantIdIndex(GlobalSecondaryIndex):
    """GSI for querying deals by restaurant_id"""

    class Meta:
        index_name = "restaurant-id-index"
        projection = AllProjection()
        read_capacity_units = 1
        write_capacity_units = 1

    restaurant_id = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class DealModel(Model):
    """DynamoDB model for deals"""

    class Meta:
        table_name = os.getenv("DEAL_TABLE_NAME", "mealsteals-dealdb-deals")
        region = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")

    # Primary key
    uuid = UnicodeAttribute(hash_key=True, default_for_new=lambda: str(uuid4()))

    # Foreign key to restaurant
    restaurant_id = UnicodeAttribute()

    # Deal details
    dish = UnicodeAttribute()
    price = NumberAttribute(null=True)  # Allow null prices
    day_of_week = ListAttribute(of=UnicodeAttribute)  # List of day strings
    notes = UnicodeAttribute(null=True)

    # System fields
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(null=True)

    # Soft delete fields
    is_deleted = BooleanAttribute(default=False)
    deleted_at = UTCDateTimeAttribute(null=True)

    # GSI indexes
    restaurant_id_index = RestaurantIdIndex()
    # Note: Removed day_of_week_index since ListAttribute can't be used as GSI key
    # You can query by restaurant_id and filter by day_of_week in application code

    def to_dict(self) -> dict:
        """Convert model to dictionary for serialization"""
        return {
            "uuid": self.uuid,
            "restaurant_id": self.restaurant_id,
            "dish": self.dish,
            "price": Decimal(str(self.price))
            if self.price is not None
            else None,  # Handle null prices
            "day_of_week": list(self.day_of_week)
            if self.day_of_week
            else [],  # Convert to list
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at,
        }
