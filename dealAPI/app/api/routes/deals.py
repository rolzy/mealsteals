import hashlib
import logging
import re
from datetime import datetime, timezone

import sqlalchemy as sa
from flask import request

from app import db
from app.api import bp
from app.api.errors import bad_request
from app.models import Deal, Restaurant

# Get the logger for this module
logger = logging.getLogger(__name__)


def generate_deal_hash(deal_data):
    """Generate a unique hash for a deal based on its attributes."""
    hash_input = (
        deal_data["url"]
        + deal_data["link_type"]
        + deal_data["link_text"]
        + str(deal_data["deal_info"].get("dish"))
        + str(deal_data["deal_info"].get("price"))
        + str(deal_data["deal_info"].get("day_of_week"))
    )

    # Extract date from text if it exists
    date_match = re.search(
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\b",
        deal_data["text"],
    )
    if date_match:
        hash_input += date_match.group(0)

    return hashlib.sha256(hash_input.encode()).hexdigest()


@bp.route("/deals/<int:id>", methods=["GET"])
def get_deal(id):
    return "This is a deal"
    # return db.get_or_404(Deal, id).to_dict()


@bp.route("/deals", methods=["GET"])
def get_deals():
    return "These are all the deals"
    # page = request.args.get("page", 1, type=int)
    # per_page = min(request.args.get("per_page", 10, type=int), 100)
    # return Deal.to_collection_dict(sa.select(Deal), page, per_page, "api.get_deals")


@bp.route("/deals", methods=["POST"])
def create_deal():
    data = request.get_json() or {}
    if "restaurant_id" not in data:
        return bad_request("Must include restaurant_id field.")

    restaurant_id = data.get("restaurant_id")
    restaurant = db.get_or_404(Restaurant, restaurant_id)

    output = []
    for key, value in data.items():
        if not key.startswith("https"):
            continue

        deal_data = {
            "url": key,
            "link_type": value.get("link_type"),
            "link_text": value.get("link_text"),
            "text": value.get("text"),
            "deal_info": value.get("deal_info", {}),
        }
        deal_hash = generate_deal_hash(deal_data)

        # Check if a deal with this hash already exists
        existing_deal = Deal.query.filter_by(deal_hash=deal_hash).first()
        if existing_deal:
            logger.info(f"Deal already exists: {existing_deal}")
            output.append(existing_deal.to_dict())
            continue

        deal_details = {
            "restaurant_id": restaurant_id,
            "deal_hash": deal_hash,
            "dish": None
            if deal_data["deal_info"].get("dish") == "None"
            else deal_data["deal_info"].get("dish"),
            "price": None
            if deal_data["deal_info"].get("price") == "None"
            else deal_data["deal_info"].get("price"),
            "day_of_week": None
            if deal_data["deal_info"].get("day_of_week") == "None"
            else deal_data["deal_info"].get("day_of_week"),
            "notes": None
            if value.get("deal_info", {}).get("note") == "None"
            else value.get("deal_info", {}).get("note"),
        }

        deal = Deal()
        deal.from_dict(deal_details)
        db.session.add(deal)
        db.session.commit()
        logger.info(f"Created new deal: {deal}")
        output.append(deal.to_dict())

    restaurant.from_dict({"deals_last_updated": datetime.now(timezone.utc)})
    db.session.commit()

    return output, 201


@bp.route("/deals/<int:id>", methods=["PUT"])
def update_deal():
    return "This is a restaurant"
