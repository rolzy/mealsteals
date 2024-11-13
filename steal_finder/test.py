import argparse
import json
import logging
import sys

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

    deal_finder = DealFinder(url)
    deals = deal_finder.find_deals()

    pretty_deals = json.dumps(deals, indent=2)
    logger.info(f"Nearby pubs found:\n{pretty_deals}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a url")
    parser.add_argument("address", help="The URL to use to find deals")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)",
    )

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper())
    main(args.address, log_level)
