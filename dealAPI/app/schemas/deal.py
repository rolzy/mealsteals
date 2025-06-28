import uuid as uuid_pkg
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from ..core.schemas import PersistentDeletion, TimestampSchema, UUIDSchema
from .restaurant import Restaurant


class DayOfWeek(str, Enum):
    """Enum for days of the week"""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class DealBase(BaseModel):
    """Base deal schema with core fields"""

    restaurant_id: Annotated[
        uuid_pkg.UUID, Field(description="UUID of the restaurant this deal belongs to")
    ]
    dish: Annotated[
        str,
        Field(
            min_length=1, max_length=500, examples=["Margherita Pizza", "Fish & Chips"]
        ),
    ]
    price: Annotated[
        Optional[Decimal],
        Field(default=None, ge=0, decimal_places=2, examples=[12.50, 25.00, None]),
    ]
    day_of_week: Annotated[
        List[DayOfWeek], Field(examples=[["monday", "tuesday"], ["friday"]])
    ]
    notes: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=1000,
            examples=["Available all day", "Happy hour special"],
        ),
    ]

    @field_validator('day_of_week', mode='before')
    @classmethod
    def normalize_day_of_week(cls, v):
        """Normalize day_of_week input to handle LLM variations"""
        if not v:
            # Empty list or None - assume everyday
            return [day.value for day in DayOfWeek]
        
        if isinstance(v, str):
            # Single string input
            v_lower = v.lower().strip()
            
            # Handle "everyday", "daily", "all week", etc.
            everyday_variants = [
                "everyday", "daily", "all week", "all days", "every day", 
                "7 days", "whole week", "entire week", "all"
            ]
            
            if v_lower in everyday_variants:
                return [day.value for day in DayOfWeek]
            
            # Try to match single day
            day_mapping = {
                "monday": DayOfWeek.MONDAY,
                "tuesday": DayOfWeek.TUESDAY, 
                "wednesday": DayOfWeek.WEDNESDAY,
                "thursday": DayOfWeek.THURSDAY,
                "friday": DayOfWeek.FRIDAY,
                "saturday": DayOfWeek.SATURDAY,
                "sunday": DayOfWeek.SUNDAY,
                "mon": DayOfWeek.MONDAY,
                "tue": DayOfWeek.TUESDAY,
                "wed": DayOfWeek.WEDNESDAY,
                "thu": DayOfWeek.THURSDAY,
                "fri": DayOfWeek.FRIDAY,
                "sat": DayOfWeek.SATURDAY,
                "sun": DayOfWeek.SUNDAY,
            }
            
            if v_lower in day_mapping:
                return [day_mapping[v_lower].value]
            
            # If we can't parse it, assume everyday
            return [day.value for day in DayOfWeek]
        
        if isinstance(v, list):
            # List input - process each item
            normalized_days = []
            for item in v:
                if isinstance(item, str):
                    item_lower = item.lower().strip()
                    
                    # Handle everyday variants in list
                    everyday_variants = [
                        "everyday", "daily", "all week", "all days", "every day",
                        "7 days", "whole week", "entire week", "all"
                    ]
                    
                    if item_lower in everyday_variants:
                        return [day.value for day in DayOfWeek]
                    
                    # Try to match individual days
                    day_mapping = {
                        "monday": DayOfWeek.MONDAY,
                        "tuesday": DayOfWeek.TUESDAY,
                        "wednesday": DayOfWeek.WEDNESDAY, 
                        "thursday": DayOfWeek.THURSDAY,
                        "friday": DayOfWeek.FRIDAY,
                        "saturday": DayOfWeek.SATURDAY,
                        "sunday": DayOfWeek.SUNDAY,
                        "mon": DayOfWeek.MONDAY,
                        "tue": DayOfWeek.TUESDAY,
                        "wed": DayOfWeek.WEDNESDAY,
                        "thu": DayOfWeek.THURSDAY,
                        "fri": DayOfWeek.FRIDAY,
                        "sat": DayOfWeek.SATURDAY,
                        "sun": DayOfWeek.SUNDAY,
                    }
                    
                    if item_lower in day_mapping:
                        normalized_days.append(day_mapping[item_lower].value)
                elif isinstance(item, DayOfWeek):
                    normalized_days.append(item.value)
            
            # If we got some valid days, return them; otherwise assume everyday
            return normalized_days if normalized_days else [day.value for day in DayOfWeek]
        
        # Fallback - assume everyday
        return [day.value for day in DayOfWeek]

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, v):
        """Convert price to Decimal for precise currency handling"""
        if v is not None and isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v

    @field_serializer("restaurant_id")
    def serialize_restaurant_id(self, restaurant_id: uuid_pkg.UUID, _info: Any) -> str:
        """Serialize restaurant_id UUID to string for JSON compatibility"""
        return str(restaurant_id)


class Deal(DealBase, TimestampSchema, UUIDSchema, PersistentDeletion):
    """Full deal model with system fields"""

    pass


class DealCreate(DealBase):
    """Schema for creating a new deal"""

    model_config = ConfigDict(extra="forbid")


class DealUpdate(BaseModel):
    """Schema for updating an existing deal"""

    dish: Annotated[Optional[str], Field(default=None, min_length=1, max_length=500)]
    price: Annotated[Optional[Decimal], Field(default=None, ge=0, decimal_places=2)]
    day_of_week: Annotated[Optional[List[DayOfWeek]], Field(default=None)]
    notes: Annotated[Optional[str], Field(default=None, max_length=1000)]

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, v):
        """Convert price to Decimal for precise currency handling"""
        if v is not None and isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v

    model_config = ConfigDict(extra="forbid")


class DealWithRestaurant(Deal):
    """Deal schema that includes restaurant information"""

    restaurant: "Restaurant"


class RestaurantWithDeals(BaseModel):
    """Restaurant schema that includes its deals"""

    restaurant: "Restaurant"
    deals: List[Deal] = Field(default_factory=list)


class RestaurantWithDealsForDay(BaseModel):
    """Restaurant schema that includes its deals for a specific day"""
    restaurant: "Restaurant"
    deals: List[Deal] = Field(default_factory=list)
    day_of_week: DayOfWeek
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class RestaurantsWithDealsForDayResponse(BaseModel):
    """Response schema for restaurants with deals for a specific day"""
    message: str
    day_of_week: DayOfWeek
    restaurants_found: int
    restaurants: List[RestaurantWithDealsForDay]
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


RestaurantWithDeals.model_rebuild()
RestaurantWithDealsForDay.model_rebuild()


class DealSearchRequest(BaseModel):
    """Request schema for deal search"""

    restaurant_id: Annotated[
        Optional[uuid_pkg.UUID],
        Field(default=None, description="Filter deals by restaurant"),
    ]
    day_of_week: Annotated[
        Optional[List[DayOfWeek]],
        Field(default=None, description="Filter deals by a list of days of the week"),
    ]
    max_price: Annotated[
        Optional[Decimal], Field(default=None, ge=0, description="Maximum price filter")
    ]
    dish_search: Annotated[
        Optional[str],
        Field(default=None, min_length=1, description="Search in dish names"),
    ]

    @field_validator("max_price", mode="before")
    @classmethod
    def validate_max_price(cls, v):
        """Convert max_price to Decimal"""
        if v is not None and isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v


class DealSearchResponse(BaseModel):
    """Response schema for deal search"""

    message: str
    deals_found: int
    deals: List[Deal]


class WebScrapedDealData(BaseModel):
    """Raw deal data from web scraping Lambda function"""

    dish: str
    price: Optional[Decimal] = None
    day_of_week: List[DayOfWeek]
    notes: Optional[str] = None

    @field_validator("day_of_week", mode="before")
    @classmethod
    def normalize_day_of_week_scraped(cls, v):
        """Normalize day_of_week input to handle LLM variations (same as DealBase)"""
        if not v:
            # Empty list or None - assume everyday
            return [day.value for day in DayOfWeek]
        
        if isinstance(v, str):
            # Single string input
            v_lower = v.lower().strip()
            
            # Handle "everyday", "daily", "all week", etc.
            everyday_variants = [
                "everyday", "daily", "all week", "all days", "every day", 
                "7 days", "whole week", "entire week", "all"
            ]
            
            if v_lower in everyday_variants:
                return [day.value for day in DayOfWeek]
            
            # Try to match single day
            day_mapping = {
                "monday": DayOfWeek.MONDAY,
                "tuesday": DayOfWeek.TUESDAY, 
                "wednesday": DayOfWeek.WEDNESDAY,
                "thursday": DayOfWeek.THURSDAY,
                "friday": DayOfWeek.FRIDAY,
                "saturday": DayOfWeek.SATURDAY,
                "sunday": DayOfWeek.SUNDAY,
                "mon": DayOfWeek.MONDAY,
                "tue": DayOfWeek.TUESDAY,
                "wed": DayOfWeek.WEDNESDAY,
                "thu": DayOfWeek.THURSDAY,
                "fri": DayOfWeek.FRIDAY,
                "sat": DayOfWeek.SATURDAY,
                "sun": DayOfWeek.SUNDAY,
            }
            
            if v_lower in day_mapping:
                return [day_mapping[v_lower].value]
            
            # If we can't parse it, assume everyday
            return [day.value for day in DayOfWeek]
        
        if isinstance(v, list):
            # List input - process each item
            normalized_days = []
            for item in v:
                if isinstance(item, str):
                    item_lower = item.lower().strip()
                    
                    # Handle everyday variants in list
                    everyday_variants = [
                        "everyday", "daily", "all week", "all days", "every day",
                        "7 days", "whole week", "entire week", "all"
                    ]
                    
                    if item_lower in everyday_variants:
                        return [day.value for day in DayOfWeek]
                    
                    # Try to match individual days
                    day_mapping = {
                        "monday": DayOfWeek.MONDAY,
                        "tuesday": DayOfWeek.TUESDAY,
                        "wednesday": DayOfWeek.WEDNESDAY, 
                        "thursday": DayOfWeek.THURSDAY,
                        "friday": DayOfWeek.FRIDAY,
                        "saturday": DayOfWeek.SATURDAY,
                        "sunday": DayOfWeek.SUNDAY,
                        "mon": DayOfWeek.MONDAY,
                        "tue": DayOfWeek.TUESDAY,
                        "wed": DayOfWeek.WEDNESDAY,
                        "thu": DayOfWeek.THURSDAY,
                        "fri": DayOfWeek.FRIDAY,
                        "sat": DayOfWeek.SATURDAY,
                        "sun": DayOfWeek.SUNDAY,
                    }
                    
                    if item_lower in day_mapping:
                        normalized_days.append(day_mapping[item_lower].value)
                elif isinstance(item, DayOfWeek):
                    normalized_days.append(item.value)
            
            # If we got some valid days, return them; otherwise assume everyday
            return normalized_days if normalized_days else [day.value for day in DayOfWeek]
        
        # Fallback - assume everyday
        return [day.value for day in DayOfWeek]

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, v):
        """Convert price to Decimal"""
        if v is not None and isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v


class BulkDealCreateRequest(BaseModel):
    """Schema for creating multiple deals for a restaurant"""

    restaurant_id: uuid_pkg.UUID
    deals: List[WebScrapedDealData]


class BulkDealCreateResponse(BaseModel):
    """Response schema for bulk deal creation"""

    message: str
    restaurant_id: uuid_pkg.UUID
    deals_created: int
    deals_updated: int
    deals: List[Deal]
