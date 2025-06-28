from typing import Annotated, List, Optional, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from ..core.schemas import PersistentDeletion, TimestampSchema, UUIDSchema

# Import only for type checking to avoid circular imports
if TYPE_CHECKING:
    from .deal import Deal


class RestaurantBase(BaseModel):
    gmaps_id: Annotated[
        str, Field(min_length=1, examples=["ChIJN1t_tDeuEmsRUsoyG83frY4"])
    ]
    url: Annotated[HttpUrl, Field(examples=["https://example-restaurant.com"])]
    name: Annotated[str, Field(min_length=1, max_length=8192, examples=["Pizza Place"])]
    venue_type: Annotated[
        Optional[List[str]],
        Field(default=None, max_length=255, examples=[["Restaurant"], ["Cafe", "Bar"]]),
    ]
    open_hours: Annotated[
        List[str],
        Field(
            default=None,
            examples=[
                [
                    "Monday: 5:30\u202fAM\u2009–\u20094:00\u202fAM",
                    "Tuesday: 5:30\u202fAM\u2009–\u20094:00\u202fAM",
                ]
            ],
        ),
    ]
    street_address: Annotated[str, Field(min_length=1, examples=["123 Main Street"])]
    latitude: Annotated[float, Field(ge=-90, le=90, examples=[-33.8688])]
    longitude: Annotated[float, Field(ge=-180, le=180, examples=[151.2093])]


class Restaurant(RestaurantBase, TimestampSchema, UUIDSchema, PersistentDeletion):
    cuisine: Annotated[
        Optional[str],
        Field(default=None, max_length=255, examples=["Italian", "Chinese", "Mexican"]),
    ]
    suburb: Annotated[
        Optional[str], Field(default=None, examples=["Downtown", "Suburbs"])
    ]
    state: Annotated[Optional[str], Field(default=None, examples=["NSW", "VIC", "QLD"])]
    postcode: Annotated[Optional[str], Field(default=None, examples=["2000", "3000"])]
    country: Annotated[
        Optional[str], Field(default=None, examples=["Australia", "United States"])
    ]
    timezone: Annotated[
        Optional[str], Field(default=None, examples=["Australia/Sydney", "Australia/Melbourne"])
    ]


class RestaurantCreate(RestaurantBase):
    # Additional fields that can be provided during creation
    cuisine: Annotated[
        Optional[str],
        Field(default=None, max_length=255, examples=["Italian", "Chinese", "Mexican"]),
    ]
    suburb: Annotated[
        Optional[str], Field(default=None, examples=["Downtown", "Suburbs"])
    ]
    state: Annotated[Optional[str], Field(default=None, examples=["NSW", "VIC", "QLD"])]
    postcode: Annotated[Optional[str], Field(default=None, examples=["2000", "3000"])]
    country: Annotated[
        Optional[str], Field(default=None, examples=["Australia", "United States"])
    ]
    timezone: Annotated[
        Optional[str], Field(default=None, examples=["Australia/Sydney", "Australia/Melbourne"])
    ]
    
    model_config = ConfigDict(extra="forbid")


class RestaurantUpdate(RestaurantBase):
    # Additional fields that can be updated (excluding timezone to preserve existing value)
    cuisine: Annotated[
        Optional[str],
        Field(default=None, max_length=255, examples=["Italian", "Chinese", "Mexican"]),
    ]
    suburb: Annotated[
        Optional[str], Field(default=None, examples=["Downtown", "Suburbs"])
    ]
    state: Annotated[Optional[str], Field(default=None, examples=["NSW", "VIC", "QLD"])]
    postcode: Annotated[Optional[str], Field(default=None, examples=["2000", "3000"])]
    country: Annotated[
        Optional[str], Field(default=None, examples=["Australia", "United States"])
    ]
    # Note: timezone is intentionally excluded to preserve existing timezone
    
    model_config = ConfigDict(extra="forbid")


class GoogleMapsRestaurantData(BaseModel):
    """Raw restaurant data from Google Maps API"""

    gmaps_id: str
    name: str
    url: HttpUrl
    venue_type: Optional[List[str]] = None
    open_hours: List[str]
    street_address: str
    latitude: float
    longitude: float


class RestaurantSearchRequest(BaseModel):
    """Request schema for restaurant search"""

    address: str
    radius: Annotated[Optional[int], Field(default=5000)]  # Default 5km radius


class RestaurantSearchResponse(BaseModel):
    """Response schema for restaurant search"""

    message: str
    restaurants_found: int
    restaurants_created: int
    restaurants_updated: int


class RestaurantSearchResultResponse(BaseModel):
    """Response schema for restaurant search that returns actual restaurants"""

    message: str
    restaurants_found: int
    restaurants_created: int
    restaurants_updated: int
    restaurants: List[Restaurant]  # The actual filtered restaurants
