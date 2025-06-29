import base64
import copy
import json
import logging
import os
import sys
import traceback
import uuid
from datetime import datetime, timezone
from decimal import Context, Decimal
from urllib.parse import urljoin

import anthropic
import boto3
import httpx
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightGeneralError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from repository.deal_repository import save_deals

# Get the logger for this module
logger = logging.getLogger()
logger.setLevel("INFO")

ANTHROPIC_API_KEY_SECRET_ARN = os.getenv("ANTHROPIC_API_KEY_SECRET_ARN")
ANTHROPIC_MODEL = "claude-3-haiku-20240307"

DEAL_PAGE_KEYWORDS = [
    "special",
    "specials",
    "deal",
    "deals",
    "promotion",
    "promotions",
    "offer",
    "offers",
    "happy hour",
    "weekly",
    "daily",
    "discount",
    "featured",
    "what",
    "restaurant",
]

DEAL_SPECIFIC_KEYWORDS = [
    "special",
    "specials",
    "deal",
    "deals",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "daily",
    "wings",
    "parm",
    "steak",
    "pizza",
    "roast",
]

DEAL_SPECIFIC_BLACKLIST = ["steakhouse"]

IMG_FILE_EXTENSIONS = ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "svg"]


def get_secret():
    session = boto3.Session()
    client = session.client(service_name="secretsmanager", region_name="ap-southeast-2")
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=ANTHROPIC_API_KEY_SECRET_ARN
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
ANTHROPIC_API_KEY = get_secret()


class DealScraper:
    def __init__(self, url, restaurant_id) -> None:
        self.url = url
        self.restaurant_id = restaurant_id
        self.deals = {}

        self.claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def __extract_text_from_html(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove unwanted elements, including common cookie consent dialogs
        for element in soup(
            [
                "script",
                "style",
                "svg",
                "header",
                "nav",
                "footer",
            ]
        ):
            element.decompose()

        # More specific selectors for cookie consent and GDPR-related elements
        cookie_selectors = [
            "div[class*='cookie' i]",
            "div[id*='cookie' i]",
            "div[class*='consent' i]",
            "div[id*='consent' i]",
            "div[class*='gdpr' i]",
            "div[id*='gdpr' i]",
            "div[aria-label*='cookie' i]",
            "div[aria-label*='consent' i]",
            "#cookieConsent",
            "#gdprConsent",
            ".cookie-banner",
            ".consent-banner",
        ]
        for selector in cookie_selectors:
            for element in soup.select(selector):
                element.decompose()

        # Extract text from remaining content
        texts = soup.stripped_strings
        extracted_text = " ".join(text for text in texts if len(text) > 1)

        # Clean up the extracted text
        cleaned_text = " ".join(extracted_text.split())

        return cleaned_text

    def __extract_deal_details_from_text(self, text):
        response = self.claude_client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=512,
            temperature=0.0,
            system="You are a helpful assistant that extracts specific deal information from restaurant website text. Your task is to identify the dish on special, the day it's offered, and its price. Provide only this information in a JSON format with keys 'dish', 'price', and 'day_of_week'. If any information is missing, use null for that key. For day_of_week, use lowercase day names like 'monday', 'tuesday', etc.",
            messages=[
                {
                    "role": "user",
                    "content": f"Extract the deal information from the following text and return it in JSON format:\n\n{text}",
                }
            ],
        )

        # Try and save response as JSON
        # If the JSON decoder returns an error, the deal probably doesn't exist, return n/a
        try:
            json_string = json.loads(response.content[0].text)
            logger.debug(f"Extracted deal from text: {json_string}")
        except json.decoder.JSONDecodeError:
            logger.warning("Deal detail extraction failed.")
            json_string = {"dish": None, "price": None, "day_of_week": None}
        return json_string

    def __extract_deal_details_from_image(self, image_url):
        image_response = httpx.get(image_url)

        # Extract the image content type from the image header
        image_content_type = image_response.headers["content-type"]
        if image_content_type not in ("image/png", "image/jpeg", "image/gif"):
            logger.debug("invalid type")
            return "n/a"

        image_data = base64.standard_b64encode(httpx.get(image_url).content).decode(
            "utf-8"
        )

        response = self.claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            temperature=0.0,
            system="You are a helpful assistant that extracts specific deal information from images. Your task is to identify the dish on special, the day it's offered, and its price. Provide only this information in a JSON format with keys 'dish', 'price', and 'day_of_week'. If you have any additional information, you can add a new 'notes' key and write it down there. If any information is missing, use null for that key. If there are multiple deals, return a list of JSON dictionaries. For day_of_week, use lowercase day names like 'monday', 'tuesday', etc.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_content_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Extract the deal information from the image and return it in JSON format.",
                        },
                    ],
                }
            ],
        )

        logger.debug(f"Response from claude: {response.content[0].text}")
        # Try and save response as JSON
        # If the JSON decoder returns an error, the deal probably doesn't exist, return n/a
        try:
            json_string = json.loads(response.content[0].text)
            logger.debug(f"Extracted deal from image: {json_string}")
        except json.decoder.JSONDecodeError:
            logger.warning("Deal detail extraction failed.")
            json_string = {"dish": None, "price": None, "day_of_week": None}

        return json_string

    def __has_large_image(self, page):
        # Find images that are large relative to the viewport size
        large_image_src = page.evaluate("""
            () => {
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                const images = Array.from(document.querySelectorAll('img'));
                
                // Sort images by their area relative to the viewport
                const sortedImages = images.sort((a, b) => {
                    const areaA = (a.width * a.height) / (viewportWidth * viewportHeight);
                    const areaB = (b.width * b.height) / (viewportWidth * viewportHeight);
                    return areaB - areaA;
                });

                // Find the first image that's at least 30% of viewport width or height
                const largeImage = sortedImages.find(img => 
                    img.width / viewportWidth > 0.3 || img.height / viewportHeight > 0.3
                );

                return largeImage ? largeImage.src : null;
            }
        """)
        logger.debug(f"Largest image found: {large_image_src}")
        return large_image_src

    def find_deals_page(self):
        logger.info(f"Finding pages that could contain deals for {self.url}")
        deals_links = []
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir="/tmp/playwright",
                headless=True,
                args=["--disable-gpu", "--single-process"],
            )
            page = browser.new_page()

            try:
                page.goto(self.url, wait_until="load")

                # First pass: Look for obvious deals-related links
                for link in page.get_by_role("link").all():
                    try:
                        text = link.text_content().lower().strip()
                        href = link.get_attribute("href")

                        # Skip social media and external links
                        if href and not any(
                            ext in href
                            for ext in [
                                "facebook.com",
                                "instagram.com",
                                "twitter.com",
                                "mailto",
                            ]
                        ):
                            # Check if link text contains deal keywords
                            if any(keyword in text for keyword in DEAL_PAGE_KEYWORDS):
                                logger.debug(f"Add {href} to first pass links")
                                full_url = urljoin(self.url, href)
                                deals_links.append(full_url)
                    except Exception:
                        continue

                logger.debug(f"First pass links: {deals_links}")

                # Second pass: Get deal-specific links
                for link in deals_links:
                    page.goto(link, wait_until="load")

                    # First pass: Look for obvious deals-related links
                    for link in page.get_by_role("link", include_hidden=True).all():
                        try:
                            text = link.text_content().lower().strip()
                            href = link.get_attribute("href")

                            if href.endswith(tuple(IMG_FILE_EXTENSIONS)):
                                link_type = "image"
                            else:
                                link_type = "text"

                            # Skip social media and external links
                            if href and not any(
                                ext in href
                                for ext in [
                                    "facebook.com",
                                    "instagram.com",
                                    "twitter.com",
                                    "mailto",
                                ]
                            ):
                                # Check if link text contains deal keywords
                                if any(
                                    keyword in text
                                    for keyword in DEAL_SPECIFIC_KEYWORDS
                                ) and not any(
                                    keyword in text
                                    for keyword in DEAL_SPECIFIC_BLACKLIST
                                ):
                                    self.deals[href] = {}
                                    self.deals[href]["link_type"] = link_type
                                    self.deals[href]["link_text"] = text
                                elif (
                                    link_type == "image"
                                    and any(
                                        keyword in href.lower()
                                        for keyword in DEAL_SPECIFIC_KEYWORDS
                                    )
                                    and not any(
                                        keyword in text
                                        for keyword in DEAL_SPECIFIC_BLACKLIST
                                    )
                                ):
                                    self.deals[href] = {}
                                    self.deals[href]["link_type"] = link_type
                                    self.deals[href]["link_text"] = text
                                    self.deals[href]["image_link"] = href

                        except Exception:
                            continue

                logger.debug(f"Second pass links: {json.dumps(self.deals, indent=2)}")
            except PlaywrightTimeoutError as e:
                logger.error(f"Timeout trying to reach {self.url}")
                logger.error(traceback.format_exc())
                raise Exception(f"Timeout error: {str(e)}") from e
            except PlaywrightGeneralError as e:
                logger.error(f"Cannot reach {self.url}")
                logger.error(traceback.format_exc())
                raise Exception(f"Playwright error: {str(e)}") from e
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                logger.error(traceback.format_exc())
                raise Exception(f"Unexpected error: {str(e)}") from e
            finally:
                browser.close()

    def find_deal_details(self, link):
        logger.info(f"Finding deal information in the page {link}")
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir="/tmp/playwright",
                headless=True,
                args=["--disable-gpu", "--single-process"],
            )
            page = browser.new_page()

            try:
                page.goto(link, wait_until="load")

                html_content = page.content()
                cleaned_text = self.__extract_text_from_html(html_content)

                logger.debug(f"LINK: {link}")
                logger.debug(f"EXTRACTED TEXT: {cleaned_text}")

                deal_info = self.__extract_deal_details_from_text(cleaned_text)
                logger.debug(f"DEAL_INFO: {deal_info}")

                # If there are any null entries in the deal info, look for more info
                if any([val is None for val in deal_info.values()]):
                    logger.debug("Missing deal info, trying to extract more info...")

                    # Try and find a large image to extract deal info
                    image_link = self.__has_large_image(page)
                    if image_link and image_link.startswith(("https", "http")):
                        self.deals[link]["link_type"] = "image"
                        self.deals[link]["image_link"] = image_link
                        logger.debug("Image found, sending request to vision model")

                        if deal_info != "n/a":
                            deal_info = self.__extract_deal_details_from_image(
                                image_link
                            )
                    else:
                        logger.debug("No more methods available, giving up...")

                self.deals[link]["text"] = cleaned_text
                self.deals[link]["deal_info"] = deal_info
            except PlaywrightTimeoutError as e:
                logger.error(f"Timeout trying to reach {self.url}")
                logger.error(traceback.format_exc())
                raise Exception(f"Timeout error: {str(e)}") from e
            except PlaywrightGeneralError as e:
                logger.error(f"Cannot reach {self.url}")
                logger.error(traceback.format_exc())
                raise Exception(f"Playwright error: {str(e)}") from e
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                logger.error(traceback.format_exc())
                raise Exception(f"Unexpected error: {str(e)}") from e
            finally:
                browser.close()

    def find_deals(self):
        # Find pages in the website that could contain specials
        self.find_deals_page()

        # For each deals link, find specific deals
        for link, _ in self.deals.items():
            self.find_deal_details(link)

        # Save the deals to DynamoDB
        try:
            deals_to_save = []
            for deal_details in self.deals.values():
                deal_info = deal_details.get("deal_info")
                if deal_info:
                    # Handle case where Claude returns a list of deals
                    if isinstance(deal_info, list):
                        for deal in deal_info:
                            if deal and deal.get("dish"):
                                deals_to_save.append(deal)
                    elif deal_info.get("dish"):
                        deals_to_save.append(deal_info)

            logger.info(
                f"Found {len(deals_to_save)} deals to save for restaurant {self.restaurant_id}"
            )
            save_deals(deals_to_save, self.restaurant_id)
        except Exception as e:
            logger.error(f"Unexpected error while saving deal: {str(e)}")
            logger.error(traceback.format_exc())

        return self.deals


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)


def handler(event, context):
    # Extract event details from SQS payload
    if "Records" in event:
        # If the event is from SQS, extract the first record
        record = event["Records"][0]
        event = json.loads(record["body"])

    logger.info(f"Received event: {json.dumps(event)}")

    url = event.get("url")
    restaurant_id = event.get("restaurant_id")

    deal_finder = DealScraper(url, restaurant_id)
    try:
        deals_data = deal_finder.find_deals()

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Deals saved successfully", "deals": deals_data},
                cls=DecimalEncoder,
            ),
        }
    except Exception as e:
        logger.error(f"Error in Lambda handler: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}, cls=DecimalEncoder),
        }
