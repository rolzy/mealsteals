from pathlib import Path

import pytest

from src import DealFinder

path = Path(__file__).parent


@pytest.mark.slow
def test_find_deals_page_1():
    test_url = "https://www.tingalpahotel.com.au/"
    deal_finder = DealFinder(test_url)
    EXPECTED_URLS = [
        "https://www.tingalpahotel.com.au/tingalpa-hotel-blog/wing-it-monday/",
        "https://www.tingalpahotel.com.au/tingalpa-hotel-blog/thursday-parmy-night/",
        "https://www.tingalpahotel.com.au/tingalpa-hotel-blog/tuesday-rump-day/",
    ]
    deal_finder.find_deals_page()
    deal_urls = list(deal_finder.deals.keys())
    assert all([url in deal_urls for url in EXPECTED_URLS])


@pytest.mark.slow
def test_find_deals_page_2():
    test_url = "https://pineapplehotel.com.au/"
    deal_finder = DealFinder(test_url)
    EXPECTED_URLS = ["https://pineapplehotel.com.au/whats-on/dinner-specials/"]
    deal_finder.find_deals_page()
    deal_urls = list(deal_finder.deals.keys())
    assert all([url in deal_urls for url in EXPECTED_URLS])


def test_extract_text_from_html():
    test_url = "https://www.tingalpahotel.com.au/"
    deal_finder = DealFinder(test_url)
    with open(path / "data/test_extract_text_from_html_input.html", "r") as f:
        html = f.read()
    with open(path / "data/test_extract_text_from_html_output.txt", "r") as f:
        EXPECTED_TEXT = f.read().strip()

    extracted_text = deal_finder._DealFinder__extract_text_from_html(html)
    assert extracted_text == EXPECTED_TEXT


@pytest.mark.slow
def test_extract_deal_details_from_text_1():
    test_url = "https://www.tingalpahotel.com.au/"
    deal_finder = DealFinder(test_url)
    with open(path / "data/test_extract_deal_details_from_text_input_1.txt", "r") as f:
        input = f.read()
    EXPECTED_DEAL = {
        "dish": "1kg of Chicken Wings",
        "price": 19.9,
        "day_of_week": "Monday",
    }

    deal_info = deal_finder._DealFinder__extract_deal_details_from_text(input)
    assert deal_info == EXPECTED_DEAL


@pytest.mark.slow
def test_extract_deal_details_from_text_2():
    # Expect text without deal infomation to return n/a
    test_url = "https://pineapplehotel.com.au/"
    deal_finder = DealFinder(test_url)
    with open(path / "data/test_extract_deal_details_from_text_input_2.txt", "r") as f:
        input = f.read()
    EXPECTED_DEAL = {
        "dish": "Dinner Specials",
        "price": None,
        "day_of_week": "Sunday - Friday",
    }

    deal_info = deal_finder._DealFinder__extract_deal_details_from_text(input)
    assert deal_info == EXPECTED_DEAL


@pytest.mark.slow
def test_extract_deal_details_from_image():
    # Expect text without deal infomation to return n/a
    test_url = "https://pineapplehotel.com.au/wp-content/uploads/dinner-special-tri-folds-instagram1080.jpg"
    deal_finder = DealFinder(test_url)
    EXPECTED_DEAL = [
        {"day_of_week": "Monday", "dish": "Gourmet pizza", "price": 18},
        {
            "day_of_week": "Monday",
            "dish": "300g rump w/ chips, salad & sauce",
            "price": 22,
        },
        {
            "day_of_week": "Tuesday",
            "dish": "200g rump w/ chips, salad & sauce",
            "price": 16,
        },
        {
            "day_of_week": "Tuesday",
            "dish": "300g rump w/ chips, salad & sauce",
            "price": 22,
        },
        {
            "day_of_week": "Wednesday",
            "dish": "Chicken schnitty w/ chips & salad",
            "price": 18,
        },
        {
            "day_of_week": "Wednesday",
            "dish": "300g rump w/ chips, salad & sauce",
            "price": 22,
        },
        {
            "day_of_week": "Thursday",
            "dish": "200g rump w/ chips, salad & sauce",
            "price": 16,
        },
        {
            "day_of_week": "Thursday",
            "dish": "300g rump w/ chips, salad & sauce",
            "price": 22,
        },
        {
            "day_of_week": "Friday",
            "dish": "300g rump w/ chips, salad & sauce",
            "price": 22,
        },
        {
            "day_of_week": "Friday",
            "dish": "$1 wings (Spicy Buffalo or Smokey BBQ)",
            "price": 1,
        },
        {"day_of_week": "Sunday", "dish": "Roast of the day", "price": 18},
        {
            "day_of_week": "Sunday",
            "dish": "300g rump w/ chips, salad & sauce",
            "price": 22,
        },
    ]
    deal_info = deal_finder._DealFinder__extract_deal_details_from_image(test_url)
    assert deal_info == EXPECTED_DEAL
    pass
