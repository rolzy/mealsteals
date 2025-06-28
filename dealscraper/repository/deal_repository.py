import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Context, Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def get_current_timestamp() -> str:
    """
    Get current UTC timestamp in the format expected by the FastAPI application.
    Removes the colon from timezone offset (+00:00 -> +0000)
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "+0000")


def get_deals_by_restaurant_id(restaurant_id: str) -> list[dict]:
    """
    Retrieves all active (non-deleted) deals for a given restaurant from the DynamoDB table.

    Args:
        restaurant_id: The ID of the restaurant.

    Returns:
        A list of deal dictionaries.
    """
    dynamodb = boto3.resource("dynamodb")
    table_name = os.getenv("DEAL_TABLE_NAME", "deals")
    table = dynamodb.Table(table_name)

    try:
        response = table.query(
            IndexName="restaurant-id-index",
            KeyConditionExpression="restaurant_id = :rid",
            FilterExpression="is_deleted = :deleted",
            ExpressionAttributeValues={":rid": restaurant_id, ":deleted": False},
        )
        return response.get("Items", [])
    except ClientError as e:
        logger.error(f"Error querying deals for restaurant {restaurant_id}: {e}")
        return []


def normalize_deal_data(deal: dict, restaurant_id: str) -> dict:
    """
    Normalizes scraped deal data to match the expected database format.

    Args:
        deal: Raw deal data from scraper
        restaurant_id: The restaurant ID to associate with the deal

    Returns:
        Normalized deal dictionary
    """
    normalized = deal.copy()

    # Add restaurant_id
    normalized["restaurant_id"] = restaurant_id

    # Normalize day_of_week to a list
    if "day_of_week" in normalized and normalized["day_of_week"] is not None:
        if isinstance(normalized["day_of_week"], str):
            normalized["day_of_week"] = [normalized["day_of_week"].lower()]
        elif isinstance(normalized["day_of_week"], list):
            normalized["day_of_week"] = [
                day.lower() if isinstance(day, str) else day
                for day in normalized["day_of_week"]
            ]
    else:
        normalized["day_of_week"] = []

    # Normalize price to Decimal
    if "price" in normalized and normalized["price"] is not None:
        try:
            # Handle various price formats
            price_str = (
                str(normalized["price"]).replace("$", "").replace(",", "").strip()
            )

            # Skip if empty or invalid
            if not price_str or price_str.lower() in ["null", "none", "n/a", ""]:
                logger.warning(
                    f"Invalid price value: {normalized['price']}, setting to None"
                )
                normalized["price"] = None
            else:
                normalized["price"] = Decimal(price_str).quantize(Decimal("0.01"))
        except (ValueError, TypeError, Exception) as e:
            logger.warning(
                f"Could not parse price: {normalized['price']} - {e}, setting to None"
            )
            normalized["price"] = None
    else:
        normalized["price"] = None

    # Normalize dish name
    if "dish" in normalized and normalized["dish"] is not None:
        normalized["dish"] = str(normalized["dish"]).strip()

    return normalized


def deals_match(scraped_deal: dict, existing_deal: dict) -> bool:
    """
    Determines if a scraped deal matches an existing deal.

    Args:
        scraped_deal: Normalized scraped deal
        existing_deal: Existing deal from database

    Returns:
        True if deals match, False otherwise
    """
    # Compare dish names (case-insensitive)
    if scraped_deal.get("dish", "").lower() != existing_deal.get("dish", "").lower():
        return False

    # Compare days of week (normalized to lowercase lists)
    scraped_days = set(scraped_deal.get("day_of_week", []))
    existing_days = existing_deal.get("day_of_week", [])

    # Handle both list and string formats for existing deals
    if isinstance(existing_days, str):
        existing_days = [existing_days]
    elif not isinstance(existing_days, list):
        existing_days = []

    existing_days = set(
        [day.lower() if isinstance(day, str) else day for day in existing_days]
    )

    return scraped_days == existing_days


def deal_needs_update(scraped_deal: dict, existing_deal: dict) -> bool:
    """
    Determines if an existing deal needs to be updated based on scraped data.

    Args:
        scraped_deal: Normalized scraped deal
        existing_deal: Existing deal from database

    Returns:
        True if deal needs update, False otherwise
    """
    # Compare prices
    scraped_price = scraped_deal.get("price")
    existing_price = existing_deal.get("price")

    # Convert existing price to Decimal if it's not already
    if existing_price is not None and not isinstance(existing_price, Decimal):
        try:
            existing_price = Decimal(str(existing_price))
        except (ValueError, TypeError):
            existing_price = None

    return scraped_price != existing_price


def save_deals(deals: list[dict], restaurant_id: str):
    """
    Saves a list of deals to the DynamoDB table with smart upsert logic.
    Compares with existing deals and creates/updates/deletes as needed.

    Args:
        deals: A list of deal dictionaries from the scraper
        restaurant_id: The restaurant ID these deals belong to
    """
    if not deals:
        logger.info(f"No deals to save for restaurant {restaurant_id}")
        return

    dynamodb = boto3.resource("dynamodb")
    table_name = os.getenv("DEAL_TABLE_NAME", "deals")
    table = dynamodb.Table(table_name)

    # Get existing active deals for this restaurant
    existing_deals = get_deals_by_restaurant_id(restaurant_id)
    logger.info(
        f"Found {len(existing_deals)} existing deals for restaurant {restaurant_id}"
    )

    # Normalize scraped deals
    normalized_deals = [
        normalize_deal_data(deal, restaurant_id) for deal in deals if deal.get("dish")
    ]
    logger.info(f"Normalized {len(normalized_deals)} scraped deals")

    # Track what we're doing
    new_deals = []
    updated_deals = []
    matched_existing_ids = set()

    # Process each scraped deal
    for scraped_deal in normalized_deals:
        found_match = False

        for existing_deal in existing_deals:
            if deals_match(scraped_deal, existing_deal):
                found_match = True
                matched_existing_ids.add(existing_deal["uuid"])

                # Check if update is needed
                if deal_needs_update(scraped_deal, existing_deal):
                    # Update the existing deal
                    updated_deal = existing_deal.copy()
                    updated_deal["price"] = scraped_deal["price"]
                    updated_deal["updated_at"] = get_current_timestamp()
                    updated_deals.append(updated_deal)
                    logger.info(
                        f"Deal will be updated: {scraped_deal['dish']} - {scraped_deal['day_of_week']}"
                    )
                else:
                    logger.info(
                        f"Deal unchanged: {scraped_deal['dish']} - {scraped_deal['day_of_week']}"
                    )
                break

        if not found_match:
            # This is a new deal
            new_deal = scraped_deal.copy()
            new_deal["uuid"] = str(uuid.uuid4())
            now = get_current_timestamp()
            new_deal["created_at"] = now
            new_deal["updated_at"] = None
            new_deal["is_deleted"] = False
            new_deal["deleted_at"] = None
            new_deals.append(new_deal)
            logger.info(
                f"New deal found: {scraped_deal['dish']} - {scraped_deal['day_of_week']}"
            )

    # Find obsolete deals (existing deals that weren't matched)
    obsolete_deals = []
    for existing_deal in existing_deals:
        if existing_deal["uuid"] not in matched_existing_ids:
            obsolete_deal = existing_deal.copy()
            now = get_current_timestamp()
            obsolete_deal["is_deleted"] = True
            obsolete_deal["deleted_at"] = now
            obsolete_deal["updated_at"] = now
            obsolete_deals.append(obsolete_deal)
            logger.info(
                f"Deal will be deleted: {existing_deal['dish']} - {existing_deal.get('day_of_week', [])}"
            )

    # Execute all changes in batch
    try:
        with table.batch_writer() as batch:
            # Create new deals
            for deal in new_deals:
                batch.put_item(Item=deal)
                logger.debug(f"Created deal: {deal['uuid']}")

            # Update existing deals
            for deal in updated_deals:
                batch.put_item(Item=deal)
                logger.debug(f"Updated deal: {deal['uuid']}")

            # Soft-delete obsolete deals
            for deal in obsolete_deals:
                batch.put_item(Item=deal)
                logger.debug(f"Deleted deal: {deal['uuid']}")

        logger.info(
            f"Deal processing complete for restaurant {restaurant_id}: "
            f"{len(new_deals)} new, {len(updated_deals)} updated, {len(obsolete_deals)} deleted"
        )

    except ClientError as e:
        logger.error(f"Error saving deals for restaurant {restaurant_id}: {e}")
        raise
