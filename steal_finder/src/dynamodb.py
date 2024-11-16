import json
import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Union

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from .restaurant import Restaurant

DYNAMODB_TABLE_NAME = "MealSteals-Restaurant-Table"

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
session = boto3.Session(profile_name=os.getenv("AWS_PROFILE"))
dyn_resource = session.resource("dynamodb")


def replace_decimals(
    obj: Union[dict, list, Decimal, float],
) -> Union[dict, list, int, float]:
    """
    Recursively replace Decimal objects with int or float.

    Args:
        obj (Union[dict, list, Decimal, float]): The object to process.

    Returns:
        Union[dict, list, int, float]: The processed object with Decimals replaced.
    """
    if isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = replace_decimals(obj[i])
        return obj
    elif isinstance(obj, dict):
        for k in obj.keys():
            obj[k] = replace_decimals(obj[k])
        return obj
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


def get_restaurant(url: str) -> Union[dict, None]:
    """
    Retrieve restaurant data from DynamoDB based on the website URL.

    Args:
        url (str): The website URL of the restaurant.

    Returns:
        dict: The restaurant data with Decimal values replaced by int or float.

    Raises:
        ClientError: If there's an error querying the DynamoDB table.
    """
    restaurant_table = dyn_resource.Table(DYNAMODB_TABLE_NAME)
    restaurant_table.load()

    try:
        response = restaurant_table.query(KeyConditionExpression=Key("website").eq(url))
    except ClientError as err:
        logger.error(
            "Couldn't query for restaurants. Here's why: %s: %s",
            url,
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise
    else:
        if response["Items"]:
            logger.info(f"Entry for {url} found")
            restaurant_info = replace_decimals(response["Items"])[0]
        else:
            logger.info(f"Entry for {url} not found")
            return None

        return Restaurant(restaurant_info)


def update_restaurants(restaurant_data: dict):
    """
    Update restaurant deals data in the DynamoDB table.

    Args:
        deals_data (dict): The deals data to be updated.

    Raises:
        ClientError: If there's an error updating the DynamoDB table.
    """
    # Convert float to decimal for DynamoDB
    # https://stackoverflow.com/questions/70343666/python-boto3-float-types-are-not-supported-use-decimal-types-instead
    restaurant_data = json.loads(json.dumps(restaurant_data), parse_float=Decimal)

    restaurant_table = dyn_resource.Table(DYNAMODB_TABLE_NAME)
    restaurant_table.load()

    try:
        with restaurant_table.batch_writer() as writer:
            for restaurant in restaurant_data:
                # Add last_updated field to each deal
                restaurant["last_updated"] = datetime.now().isoformat()
                writer.put_item(Item=restaurant)
    except ClientError as err:
        logger.error(
            "Couldn't load data into table %s. Here's why: %s: %s",
            restaurant_table.name,
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise
