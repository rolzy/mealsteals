import logging
from datetime import datetime, timedelta

from dotenv import load_dotenv

DYNAMODB_TABLE_NAME = "MealSteals-Restaurant-Table"

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class Restaurant:
    """Encapsulates an Amazon DynamoDB table of restaurant data.

    Example data structure for a movie record in this table:
        {
          "id": "ChIJS_feAfBbkWsRo7K91wKVKCU",
          "name": "Carina Leagues Club",
          "website": "http://www.carinaleagues.com.au/",
          "hours": [
            "Monday: 7:00\u202fAM\u2009\u2013\u20094:00\u202fAM",
            "Tuesday: 7:00\u202fAM\u2009\u2013\u20094:00\u202fAM",
            "Wednesday: 7:00\u202fAM\u2009\u2013\u20094:00\u202fAM",
            "Thursday: 7:00\u202fAM\u2009\u2013\u20094:00\u202fAM",
            "Friday: 7:00\u202fAM\u2009\u2013\u20094:00\u202fAM",
            "Saturday: 7:00\u202fAM\u2009\u2013\u20094:00\u202fAM",
            "Sunday: 7:00\u202fAM\u2009\u2013\u20094:00\u202fAM"
          ],
          "address": "1390 Creek Rd, Carina QLD 4152, Australia",
          "coordinates": {
            "lat": -27.4919444,
            "lng": 153.1008333
          },
          "rating": 4.2,
          "serves_beer": null,
          "serves_wine": null,
          "serves_dinner": null,
          "types": [
            "liquor_store",
            "cafe",
            "bar",
            "restaurant",
            "food",
            "point_of_interest",
            "store",
            "establishment"
          ],
          "deals": {
            "https://www.carinaleaguesclub.com.au/event/friday-night-draws-sweet-treats/": {
              "link_type": "image",
              "image_link": "https://www.carinaleaguesclub.com.au/wp-content/uploads/2024/08/CLC-Place-Holder-Header.jpg",
              "text": "Friday Night Draws - Sweet Treats - Carina Leagues Club \u00ab All Events Friday Night Draws \u2013 Sweet Treats Event Category: Regular September 6 - December 19 Up to $170,000 to be won on Friday nights until 19 December 2024. Starts 6 September 2024, draws from 7:00pm. Earn entries from 10:00am on draw days. For full Terms and Conditions, please refer to our App or reach out to the Club directly. Please note: The information located on this page is not intended for persons under the age of 18 years or patrons excluded from gaming. Add to calendar Google Calendar iCalendar Outlook 365 Outlook Live Details Start: September 6 @ 8:00 am End: December 19 @ 5:00 pm Event Category: Regular Become A Member For just $2 you can become a Club Member. You save $$ plus every cent you spend goes back into helping our local community. Sign up today and enjoy amazing value with exclusive Members-only prices on food and drinks, weekly events, and much more! Join Today",
              "link_text": "friday night draws \u2013 sweet treats",
              "deal_info": {
                "dish": null,
                "price": null,
                "day_of_week": null
              }
            }
          },
          "last_updated": "20241116-153700:00"
        }
    """

    def __init__(self, restaurant_data: dict):
        self.id = restaurant_data.get("id")
        self.name = restaurant_data.get("name")
        self.website = restaurant_data.get("website")
        self.hours = restaurant_data.get("hours", [])
        self.address = restaurant_data.get("address")
        self.coordinates = restaurant_data.get("coordinates", {})
        self.rating = restaurant_data.get("rating")
        self.serves_beer = restaurant_data.get("serves_beer")
        self.serves_wine = restaurant_data.get("serves_wine")
        self.serves_dinner = restaurant_data.get("serves_dinner")
        self.types = restaurant_data.get("types", [])
        self.deals = restaurant_data.get("deals", {})
        self.last_updated = restaurant_data.get("last_updated")

    def get_restaurant(self):
        return vars(self)

    def get_url(self):
        return self.website

    def update_deals(self, deals):
        self.deals = deals

    def recently_updated(self) -> bool:
        last_updated_str = self.last_updated
        if last_updated_str:
            last_updated = datetime.fromisoformat(last_updated_str)
            current_date = datetime.now()
            difference = current_date - last_updated
            return difference <= timedelta(days=30)
        return False
