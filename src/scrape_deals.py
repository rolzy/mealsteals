import json
import logging
import os
from urllib.parse import urljoin

import anthropic
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Get the logger for this module
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
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

        # Remove unwanted elements
        for element in soup(["script", "style", "svg", "header", "nav", "footer"]):
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
            json_string = "n/a"
        return json_string

    def find_deals_page(self):
        logger.info("Finding pages that could contain deals...")
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
                            for ext in ["facebook.com", "instagram.com", "twitter.com"]
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
                                    href.endswith(tuple(IMG_FILE_EXTENSIONS))
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

                        except Exception as e:
                            continue

                logger.debug(f"Second pass links: {json.dumps(self.deals, indent=2)}")

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
                # You might want to store or process the cleaned_text here
                # For example: self.deals[link] = cleaned_text
                self.deals[link]["text"] = cleaned_text
                self.deals[link]["deal_info"] = deal_info
            finally:
                browser.close()

    def find_deals(self):
        # Find pages in the website that could contain specials
        self.find_deals_page()

        # For each deals link, find specific deals
        for link, _ in self.deals.items():
            self.find_deal_details(link)

        return self.deals


# {
#  "https://www.tingalpahotel.com.au/tingalpa-hotel-blog/wing-it-monday/": "Wing It Monday - Tingalpa Hotel Wing It Monday Feb 28, 2024 Monday Dinner plans? Just WING it! Enjoy 1kg of our famous Chicken Wings for only $19.90 every Monday Night at the Tingalpa Hotel. Pick from fan-favourite flavours: Honey Soy BBQ Honey BBQ Chipotle Spicy Sriracha Famous Buffalo Reaper Extra Hot Can't decide? Pick up to 2 different flavours on every order! Book Now Book in for our next Wing It Monday Night special via our online table reservation system. We'll see you soon! Make a Reservation",
#  "https://www.tingalpahotel.com.au/tingalpa-hotel-blog/thursday-parmy-night/": "Thursday Parmy Night - Tingalpa Hotel Thursday Parmy Night Feb 28, 2024 $19.90 THURSDAY PARMY NIGHT Are you a true-blue Parmy lover? Then you will be happy to hear that it\u2019s Parmy Appreciation Evening every Thursday night at the Tingalpa Hotel! If you haven\u2019t already, we recommend sinking your teeth into this Australian pub favourite. Now even better than ever at a great special price. Treat yourself to a delicious, mouth-watering Parmy, sides and sauce for only $19.90. If you have a big appetite, then upgrade to our GIANT Parmy! Book Now Craving a great feed at a special price? Book a table for our next Thursday Parmy Night. We'll see you soon! Make a Reservation",
#  "https://www.tingalpahotel.com.au/tingalpa-hotel-blog/tuesday-rump-day/": "Tuesday Night Rump - Tingalpa Hotel Tuesday Night Rump Jul 15, 2021 Tuesday Night Rump Nothing is more satisfying than a mouth-watering steak at a great price! It's your steak, your way every Tuesday Night at Tingalpa Hotel. Customise your premium steak - choose your sides, sauce and your steak cooked just the way you like for only $19.90. There's even the choice to add your favourite toppers for a little extra! As a family-owned, Australian company we understand the importance of sourcing produce locally and do so wherever possible. It may cost a little extra but our produce does keep longer and arrives with minimum waste. We don\u2019t believe you can put a price on quality and the fresher the produce the more flavoursome it is. This is a proud and very powerful movement that the Hakfoort Group and Tingalpa Hotel support. We pride ourselves on our steak. Both lean and tender, this full flavoured beef is carefully chosen for breeding quality, food regine, fat and meat colour. All of these elements combined give diners the ultimate steak experience. Book or Order Ready to sink your teeth into a great steak? Tuesday's can get busy, so we encourage you to book online - or give us a call on (07) 3213 9660 to make a reservation or order takeaway. Make a Reservation Diner's Thoughts \"Wow, they don't even brag about their steaks, and they are definitely as good as \"Brisbane's Best.\" Casual pub atmosphere, awesome staff and great service. I've been holding off my review because I'd rather keep this place to myself.\" Michael Quinn Google Review"
# }
