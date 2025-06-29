import os
from datetime import datetime, timezone
from typing import List, Optional
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


class GmapsIdIndex(GlobalSecondaryIndex):
    """
    GSI for querying by gmaps_id
    """

    class Meta:
        index_name = "gmaps-id-index"
        read_capacity_units = 5
        write_capacity_units = 5
        projection = AllProjection()

    gmaps_id = UnicodeAttribute(hash_key=True)


class RestaurantModel(Model):
    """
    DynamoDB model for Restaurant data
    """

    class Meta:
        table_name = os.getenv("RESTAURANT_TABLE_NAME", "mealsteals-dealdb-restaurants")
        region = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")

    # Primary key
    uuid = UnicodeAttribute(hash_key=True, default_for_new=lambda: str(uuid4()))

    # Google Maps data
    gmaps_id = UnicodeAttribute()
    url = UnicodeAttribute()
    name = UnicodeAttribute()
    venue_type = ListAttribute(of=UnicodeAttribute, null=True)
    open_hours = ListAttribute(of=UnicodeAttribute, null=True)
    street_address = UnicodeAttribute()
    latitude = NumberAttribute()
    longitude = NumberAttribute()

    # Additional restaurant data (populated later)
    cuisine = UnicodeAttribute(null=True)
    suburb = UnicodeAttribute(null=True)
    state = UnicodeAttribute(null=True)
    postcode = UnicodeAttribute(null=True)
    country = UnicodeAttribute(null=True)
    timezone = UnicodeAttribute(
        null=True
    )  # Store timezone string (e.g., "Australia/Sydney")

    # Audit fields
    created_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(null=True)

    # Soft delete
    deleted_at = UTCDateTimeAttribute(null=True)
    is_deleted = BooleanAttribute(default=False)

    # Global Secondary Index for gmaps_id lookups
    gmaps_id_index = GmapsIdIndex()

    def save(self, **kwargs):
        """Override save to update the updated_at timestamp"""
        if not self._get_save_args()[1]["condition"]:
            # Only update timestamp if this isn't a conditional save
            self.updated_at = datetime.now(timezone.utc)
        super().save(**kwargs)

    def soft_delete(self):
        """Soft delete the restaurant"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.save()

    @classmethod
    def create_table_if_not_exists(cls):
        """Create the table if it doesn't exist"""
        if not cls.exists():
            cls.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)
            print(f"Created table: {cls.Meta.table_name}")
        else:
            print(f"Table already exists: {cls.Meta.table_name}")
