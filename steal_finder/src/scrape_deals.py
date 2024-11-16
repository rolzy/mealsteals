import base64
import json
import logging
import os
from urllib.parse import urljoin

import anthropic
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import Error as PlaywrightGeneralError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# Load environment variables from .env file
load_dotenv()

# Get the logger for this module
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
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


class DealFinder:
    def __init__(self, url) -> None:
        self.url = url
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
            system="You are a helpful assistant that extracts specific deal information from restaurant website text. Your task is to identify the dish on special, the day it's offered, and its price. Provide only this information in a JSON format with keys 'dish', 'price', and 'day_of_week'. If any information is missing, use null for that key.",
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
        except json.decoder.JSONDecodeError as e:
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

        print(f"Image content type: {image_content_type}")
        image_data = base64.standard_b64encode(httpx.get(image_url).content).decode(
            "utf-8"
        )

        response = self.claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            temperature=0.0,
            system="You are a helpful assistant that extracts specific deal information from images. Your task is to identify the dish on special, the day it's offered, and its price. Provide only this information in a JSON format with keys 'dish', 'price', and 'day_of_week'. If you have any additional information, you can add a new 'note' key and write it down there. If any information is missing, use null for that key. If there are multiple deals, return a list of JSON dictionaries.",
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
        except json.decoder.JSONDecodeError as e:
            logger.warning("Deal detail extraction failed.")
            json_string = {"dish": None, "price": None, "day_of_week": None}

        print(f"Image extraction result: {json_string}")
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
            browser = p.chromium.launch()
            page = browser.new_page()

            try:
                page.goto(self.url, wait_until="networkidle")

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
                    except Exception as e:
                        continue

                logger.debug(f"First pass links: {deals_links}")

                # Second pass: Get deal-specific links
                for link in deals_links:
                    page.goto(link, wait_until="networkidle")

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

                        except Exception as e:
                            continue

                logger.debug(f"Second pass links: {json.dumps(self.deals, indent=2)}")
            except PlaywrightTimeoutError:
                logger.error(f"Timeout trying to reach {self.url}")
            except PlaywrightGeneralError:
                logger.error(f"Cannot reach {self.url}")
            finally:
                browser.close()

    def find_deal_details(self, link):
        logger.info(f"Finding deal information in the page {link}")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            try:
                page.goto(link, wait_until="networkidle")

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
            except PlaywrightTimeoutError:
                logger.error(f"Timeout trying to reach {self.url}")
            except PlaywrightGeneralError:
                logger.error(f"Cannot reach {self.url}")
            finally:
                browser.close()

    def find_deals(self):
        # Find pages in the website that could contain specials
        self.find_deals_page()

        # For each deals link, find specific deals
        for link, _ in self.deals.items():
            self.find_deal_details(link)

        return self.deals
