import json
import logging
import os
from typing import Tuple, Union

import boto3
import googlemaps
from botocore.exceptions import ClientError

## Static Variables
GOOGLE_API_KEY_SECRET_ARN = os.getenv("GOOGLE_API_KEY_SECRET_ARN")
SEARCH_KEYWORDS = ["pub restaurants"]
TYPE_KEYWORDS = ["bar"]
TYPE_BLACKLIST = ["night_club"]

# Get the logger for this module
logger = logging.getLogger(__name__)


def get_secret():
    session = boto3.Session()
    client = session.client(service_name="secretsmanager", region_name="ap-southeast-2")
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=GOOGLE_API_KEY_SECRET_ARN
        )
    except ClientError as e:
        logger.error(f"Error fetching secret: {str(e)}")
        raise e
    else:
        if "SecretString" in get_secret_value_response:
            return get_secret_value_response["SecretString"]
        else:
            logger.error("Secret not found in the expected format")
            raise ValueError("Secret not found in the expected format")


# Fetch the Google API Key from Secrets Manager
GOOGLE_API_KEY = get_secret()

gmaps = googlemaps.Client(key=GOOGLE_API_KEY)


def get_coordinates_from_address(address: str) -> Union[Tuple[float, float], None]:
    """
    Get the coordinates (latitude, longitude) for a given address.

    Args:
    address (str): The address to geocode.

    Returns:
    Union[Tuple[float, float], None]: A tuple of (latitude, longitude) if successful, None otherwise.
    """
    try:
        result = gmaps.geocode(address)
        if result:
            location = result[0]["geometry"]["location"]
            return location["lat"], location["lng"]
        else:
            logger.error(f"Unable to geocode address: {address}")
            return None
    except Exception as e:
        logger.error(f"Error geocoding address: {str(e)}")
        return None


def find_restaurants(
    address: str, search_radius: int = 5000
) -> Union[list[dict], dict]:
    """
    Find restaurants near a given address using Google Maps API.

    This function takes an address and a search radius, geocodes the address to get coordinates,
    and then searches for restaurants within the specified radius. It filters the results based on
    predefined keywords and types.

    Args:
        address (str): The address to search around. This can be a full address, city, or any
                       location string that Google Maps can geocode.
        search_radius (int, optional): The radius (in meters) around the address to search for
                                       restaurants. Defaults to 5000 meters (5 km).

    Returns:
        Union[list[dict], None]: A list of dictionaries, where each dictionary contains details
                                 about a restaurant found. Returns None if there was an error in
                                 geocoding or if no restaurants were found. Each restaurant
                                 dictionary includes:
                                 - gmaps_id: Google Maps place ID
                                 - url: Website of the restaurant
                                 - name: Name of the restaurant
                                 - venue_type: Types of the venue as per Google Maps
                                 - open_hours: Opening hours of the restaurant
                                 - street_address: Formatted address of the restaurant
                                 - latitude: Latitude of the restaurant location
                                 - longitude: Longitude of the restaurant location

    Raises:
        No exceptions are explicitly raised, but errors are logged:
        - If the address cannot be geocoded
        - If there's an error in the Google Maps API request
        - If the 'next page' token is present (currently not implemented)

    Note:
        This function uses predefined SEARCH_KEYWORDS and TYPE_KEYWORDS to filter results.
        It also requires a valid Google Maps API key to be set in the environment variables.
    """
    coordinates = get_coordinates_from_address(address)
    if coordinates:
        latitude, longitude = coordinates
        logger.debug(
            f"Coordinates for {address}: Latitude {latitude}, Longitude {longitude}"
        )
    else:
        logger.error(f"Unable to get coordinates for the address: {address}")
        return {
            "Status": "Error",
            "Message": "Unable to get coordinates for the address",
        }

    restaurants = []

    for search_term in SEARCH_KEYWORDS:
        results = gmaps.places(
            query=search_term, location=[latitude, longitude], radius=search_radius
        )
        next_page_exist = results.get("next-page_token") is not None
        logger.debug(f"Next page exists? {next_page_exist}")
        if next_page_exist:
            logger.error("Next_page logic not implemented yet.")
            return {
                "Status": "Error",
                "Message": "gmaps Next_page logic not implemented yet.",
            }

        for result in results["results"]:
            if all([keyword in result["types"] for keyword in TYPE_KEYWORDS]):
                place_details = gmaps.place(result["place_id"])["result"]
                if place_details.get("website"):
                    pub_data = {
                        "gmaps_id": result.get("place_id"),
                        "url": place_details.get("website"),
                        "name": place_details.get("name"),
                        "venue_type": place_details.get("types"),
                        "open_hours": place_details.get("opening_hours", {}).get(
                            "weekday_text"
                        ),
                        "street_address": place_details.get("formatted_address"),
                        "latitude": place_details.get("geometry", {})
                        .get("location", {})
                        .get("lat"),
                        "longitude": place_details.get("geometry", {})
                        .get("location", {})
                        .get("lng"),
                    }
                    restaurants.append(pub_data)
                else:
                    logger.warning(
                        f"Website data not found for {place_details.get('name')}"
                    )

    return restaurants


def lambda_handler(event, context):
    address = event.get("address")
    search_radius = event.get("search_radius")
    restaurants = find_restaurants(address, search_radius)
    return restaurants
