import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone

import boto3
import sqlalchemy as sa
from flask import jsonify, request

from app import db
from app.api import bp
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


@bp.route("/restaurants/<int:id>", methods=["GET"])
def get_restaurant(id):
    return db.get_or_404(Restaurant, id).to_dict()


@bp.route("/restaurants", methods=["GET"])
def get_restaurants():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    return Restaurant.to_collection_dict(
        sa.select(Restaurant), page, per_page, "api.get_restaurants"
    )


@bp.route("/restaurants/<int:id>/deals", methods=["GET"])
def get_restaurant_deals(id):
    restaurant = db.get_or_404(Restaurant, id)

    # If the deals for the restaurant have not been updated in the last month, update them
    if restaurant.deals_last_updated is None or (
        datetime.now(timezone.utc) - restaurant.deals_last_updated
    ) > timedelta(days=30):
        logger.info(f"Updating deals for restaurant {restaurant.name}")
        payload = {"url": restaurant.url}

        # Create a Lambda client
        lambda_client = boto3.client("lambda", region_name="ap-southeast-2")
        try:
            # Invoke the Lambda function
            response = lambda_client.invoke(
                FunctionName="arn:aws:lambda:ap-southeast-2:700723066985:function:mealsteals-dealscraper",
                InvocationType="RequestResponse",
                Payload=json.dumps(payload),
            )

            # Parse the response from the Lambda function
            result = json.loads(response["Payload"].read().decode("utf-8"))

            # Check if the Lambda function returned an error
            if "errorMessage" in result:
                logger.error(
                    f"Lambda function returned an error: {result['errorMessage']}"
                )
                return jsonify(
                    {"error": "An error occurred while processing your request"}
                ), 500

        except Exception as e:
            logger.error(f"Error invoking Lambda function: {str(e)}")
            return jsonify(
                {"error": "An error occurred while processing your request"}
            ), 500

        logger.info(f"response: {response}")
        logger.info(f"Found deals: {result}")

        deals_dict = [{"deal": "this is a deal"}]
        # deal_hash = generate_deal_hash(result)

    else:
        deals = Deal.query.filter_by(restaurant_id=id).all()
        deals_dict = [deal.to_dict() for deal in deals]

    return {"restaurant_id": id, "deals": deals_dict}


@bp.route("/restaurants", methods=["POST"])
def create_restaurant():
    return "This is a restaurant"


@bp.route("/restaurants/<int:id>", methods=["PUT"])
def update_restaurant():
    return "This is a restaurant"
