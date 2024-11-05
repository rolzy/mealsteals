import argparse
import json
import logging
import sys
from datetime import datetime

from src import DealFinder


def setup_logging(log_level):
    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(log_level)
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(stdout)
    return logger


def main(url, log_level):
    logger = setup_logging(log_level)
    logger.info(f"Finding deals in: {url}")
    # Add your main logic here

    deal_finder = DealFinder(url)
    deals = deal_finder.find_deals()
    pretty_deals = json.dumps(deals, indent=2)
    logger.info(f"Deals found:\n{pretty_deals}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a URL.")
    parser.add_argument("url", help="The URL to process")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)",
    )

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper())
    main(args.url, log_level)
