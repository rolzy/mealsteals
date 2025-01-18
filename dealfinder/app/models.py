from typing import Optional

import sqlalchemy as sa
import sqlalchemy.orm as so

from app import db


class Restaurant(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    url: so.Mapped[str] = so.mapped_column(sa.String(), unique=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(), index=True)
    cuisine: so.Mapped[Optional[str]] = so.mapped_column(sa.String())
    venue_type: so.Mapped[Optional[str]] = so.mapped_column(sa.String())
    street_address: so.Mapped[str] = so.mapped_column(sa.String())
    suburb: so.Mapped[str] = so.mapped_column(sa.String())
    state: so.Mapped[str] = so.mapped_column(sa.String())
    postcode: so.Mapped[str] = so.mapped_column(sa.String())
    country: so.Mapped[str] = so.mapped_column(sa.String())
    latitude: so.Mapped[float] = so.mapped_column(sa.DECIMAL(), index=True)
    longitude: so.Mapped[float] = so.mapped_column(sa.DECIMAL(), index=True)
    deals: so.WriteOnlyMapped["Deal"] = so.relationship(back_populates="restaurant")

    def __repr__(self):
        return f"<Restaurant: {self.name}>"


class Deal(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    restaurant_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey(Restaurant.id), index=True
    )
    restaurant: so.Mapped[Restaurant] = so.relationship(back_populates="deals")
    dish: so.Mapped[Optional[str]] = so.mapped_column(sa.String(), index=True)
    price: so.Mapped[Optional[float]] = so.mapped_column(sa.DECIMAL(), index=True)
    day_of_week: so.Mapped[list[str]] = so.mapped_column(sa.ARRAY(sa.String()))
    note: so.Mapped[str] = so.mapped_column(sa.String())

    def __repr__(self):
        return (
            f"<Deal {self.id}: "
            f"Restaurant: {self.restaurant_id}, "
            f"Dish: {self.dish}, "
            f"Price: {self.price}, "
            f"DayOfWeek: {self.day_of_week}, "
            f"Notes: {self.note}>"
        )
