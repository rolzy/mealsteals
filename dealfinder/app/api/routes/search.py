import logging
import os
from typing import Tuple, Union

import googlemaps
from flask import request
from logic import find_restaurants

from app import db
from app.api import bp
from app.api.errors import bad_request
from app.models import Restaurant

# Static Variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_KEYWORDS = ["pub restaurants"]
TYPE_KEYWORDS = ["bar"]
TYPE_BLACKLIST = ["night_club"]

gmaps = googlemaps.Client(key=GOOGLE_API_KEY)

# Get the logger for this module
logger = logging.getLogger(__name__)


@bp.route("/search", methods=["POST"])
def search_restaurants():
    data = request.get_json() or {}
    if "address" not in data:
        return bad_request("Must include address field.")

    address = data.get("address")
    radius = data.get("radius", 5000)

    restaurants = find_restaurants(address, radius)
    output = []

    for place_details in restaurants:
        gmaps_id = place_details.get("gmaps_id")
        restaurant = Restaurant.query.filter_by(gmaps_id=gmaps_id).first()

        if restaurant is None:
            restaurant = Restaurant()
            restaurant.from_dict(place_details)
            db.session.add(restaurant)
            db.session.commit()
            logger.info(f"Created new restaurant: {restaurant.name}")
        else:
            logger.info(f"Found existing restaurant: {restaurant.name}")
        output.append(restaurant.to_dict())

    if not output:
        return {
            "message": "No restaurants found, please try and increase the search radius or try a different address."
        }
    return {"restaurants": output}
