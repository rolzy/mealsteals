import json
import logging
import os
from typing import Tuple, Union

import boto3
from flask import jsonify, request

# from logic import find_restaurants
from app import db
from app.api import bp
from app.api.errors import bad_request
from app.models import Restaurant

# Get the logger for this module
logger = logging.getLogger(__name__)


@bp.route("/search", methods=["POST"])
def search_restaurants():
    data = request.get_json() or {}
    if "address" not in data:
        return bad_request("Must include address field.")

    address = data.get("address")
    radius = data.get("radius", 5000)

    # Create a Lambda client
    lambda_client = boto3.client("lambda", region_name="ap-southeast-2")

    # Prepare the payload for the Lambda function
    payload = {"address": address, "radius": radius}

    try:
        # Invoke the Lambda function
        response = lambda_client.invoke(
            FunctionName="arn:aws:lambda:ap-southeast-2:700723066985:function:mealsteals-dealfinder",
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        # Parse the response from the Lambda function
        result = json.loads(response["Payload"].read().decode("utf-8"))

        # Check if the Lambda function returned an error
        if "errorMessage" in result:
            logger.error(f"Lambda function returned an error: {result['errorMessage']}")
            return jsonify(
                {"error": "An error occurred while processing your request"}
            ), 500

    except Exception as e:
        logger.error(f"Error invoking Lambda function: {str(e)}")
        return jsonify(
            {"error": "An error occurred while processing your request"}
        ), 500

    output = []

    for place_details in result:
        gmaps_id = place_details.get("gmaps_id")
        restaurant = Restaurant.query.filter_by(gmaps_id=gmaps_id).first()

        if restaurant is None:
            restaurant = Restaurant()
            restaurant.from_dict(place_details)
            db.session.add(restaurant)
            db.session.commit()
            logger.debug(f"Created new restaurant: {restaurant.name}")
        else:
            logger.debug(f"Found existing restaurant: {restaurant.name}")
        output.append(restaurant.to_dict())

    if not output:
        return {
            "message": "No restaurants found, please try and increase the search radius or try a different address."
        }

    test_website = {"url": "https://www.tingalpahotel.com.au/"}
    logger.info("Invoking the deal scraper Lambda function")
    logger.info(f"Test website: {test_website}")

    try:
        # Invoke the Lambda function
        response = lambda_client.invoke(
            FunctionName="arn:aws:lambda:ap-southeast-2:700723066985:function:mealsteals-dealscraper",
            InvocationType="RequestResponse",
            Payload=json.dumps(test_website),
        )

        # Parse the response from the Lambda function
        result = json.loads(response["Payload"].read().decode("utf-8"))

        # Check if the Lambda function returned an error
        if "errorMessage" in result:
            logger.error(f"Lambda function returned an error: {result['errorMessage']}")
            return jsonify(
                {"error": "An error occurred while processing your request"}
            ), 500

    except Exception as e:
        logger.error(f"Error invoking Lambda function: {str(e)}")
        return jsonify(
            {"error": "An error occurred while processing your request"}
        ), 500

    logger.info(f"Found deals: {result}")

    return {"restaurants": output}
