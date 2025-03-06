import datetime
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.orm as so
from flask import url_for

from app import db


class PaginatedAPIMixin(object):
    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        resources = db.paginate(query, page=page, per_page=per_page, error_out=False)

        data = {
            "items": [item.to_dict() for item in resources.items],
            "_meta": {
                "page": page,
                "per_page": per_page,
                "total_pages": resources.pages,
                "total_items": resources.total,
            },
            "_links": {
                "self": url_for(endpoint, page=page, per_page=per_page, **kwargs),
                "next": url_for(endpoint, page=page + 1, per_page=per_page, **kwargs)
                if resources.has_next
                else None,
                "prev": url_for(endpoint, page=page - 1, per_page=per_page, **kwargs)
                if resources.has_prev
                else None,
            },
        }
        return data


class Restaurant(PaginatedAPIMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    gmaps_id: so.Mapped[str] = so.mapped_column(sa.String(), unique=True)
    url: so.Mapped[str] = so.mapped_column(sa.String())
    name: so.Mapped[str] = so.mapped_column(sa.String(), index=True)
    cuisine: so.Mapped[Optional[str]] = so.mapped_column(sa.String())
    venue_type: so.Mapped[Optional[str]] = so.mapped_column(sa.String())
    open_hours: so.Mapped[Optional[str]] = so.mapped_column(sa.String())
    street_address: so.Mapped[str] = so.mapped_column(sa.String())
    suburb: so.Mapped[Optional[str]] = so.mapped_column(sa.String())
    state: so.Mapped[Optional[str]] = so.mapped_column(sa.String())
    postcode: so.Mapped[Optional[str]] = so.mapped_column(sa.String())
    country: so.Mapped[Optional[str]] = so.mapped_column(sa.String())
    latitude: so.Mapped[float] = so.mapped_column(sa.DECIMAL(), index=True)
    longitude: so.Mapped[float] = so.mapped_column(sa.DECIMAL(), index=True)
    deals: so.WriteOnlyMapped["Deal"] = so.relationship(back_populates="restaurant")
    deals_last_updated: so.Mapped[Optional[datetime.datetime]] = so.mapped_column(
        sa.DateTime(timezone=True)
    )

    def __repr__(self):
        return f"<Restaurant: {self.name}>"

    def to_dict(self):
        data = {
            "id": self.id,
            "url": self.url,
            "name": self.name,
            "cuisine": self.cuisine,
            "venue_type": self.venue_type,
            "street_address": self.street_address,
            "suburb": self.suburb,
            "state": self.state,
            "postcode": self.postcode,
            "country": self.country,
            "latitude": float(self.latitude),
            "longitude": float(self.longitude),
            "_links": {
                "self": url_for("api.get_restaurant", id=self.id),
                # "deals": url_for("api.get_deals", id=self.id),
            },
        }

        return data

    def from_dict(self, data):
        for field in [
            "gmaps_id",
            "url",
            "name",
            "cuisine",
            "venue_type",
            "street_address",
            "suburb",
            "state",
            "postcode",
            "country",
            "latitude",
            "longitude",
            "deals_last_updated",
        ]:
            if field in data:
                setattr(self, field, data[field])


class Deal(PaginatedAPIMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    restaurant_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey(Restaurant.id), index=True
    )
    deal_hash: so.Mapped[str] = so.mapped_column(sa.String(), unique=True)
    restaurant: so.Mapped[Restaurant] = so.relationship(back_populates="deals")
    dish: so.Mapped[Optional[str]] = so.mapped_column(sa.String(), index=True)
    price: so.Mapped[Optional[float]] = so.mapped_column(sa.DECIMAL(), index=True)
    day_of_week: so.Mapped[Optional[list[str]]] = so.mapped_column(
        sa.ARRAY(sa.String())
    )
    notes: so.Mapped[Optional[str]] = so.mapped_column(sa.String())

    def __repr__(self):
        return (
            f"<Deal {self.id}: "
            f"Restaurant: {self.restaurant_id}, "
            f"Hash: {self.deal_hash}, "
            f"Dish: {self.dish}, "
            f"Price: {self.price}, "
            f"DayOfWeek: {self.day_of_week}, "
            f"Notes: {self.notes}, "
        )

    def to_dict(self):
        return {
            "id": self.id,
            "restaurant_id": self.restaurant_id,
            "hash": self.deal_hash,
            "dish": self.dish,
            "price": float(self.price) if self.price is not None else None,
            "day_of_week": self.day_of_week,
            "notes": self.notes,
        }

    def from_dict(self, data):
        for field in [
            "restaurant_id",
            "deal_hash",
            "dish",
            "price",
            "notes",
        ]:
            if field in data:
                setattr(self, field, data[field])

        for field in ["day_of_week"]:
            if field in data:
                if data[field]:
                    setattr(self, field, data[field].split(","))
