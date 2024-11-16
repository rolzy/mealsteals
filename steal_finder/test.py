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


def main(mode, url, log_level):
    logger = setup_logging(log_level)

    if mode == "find-deals":
        logger.info(f"Finding deals in: {url}")

        deal_finder = DealFinder(url)
        deals = deal_finder.find_deals()

        pretty_deals = json.dumps(deals, indent=2)
        logger.info(f"Nearby pubs found:\n{pretty_deals}")
    elif mode == "write-results":
        logger.info("Write deal results in result.json to DynamoDB")

        try:
            with open("result.json", "r") as file:
                deals_dict = json.load(file)
            logger.info("Successfully read deals from result.json")
        except FileNotFoundError:
            logger.error("result.json file not found")
            return
        except json.JSONDecodeError:
            logger.error("Error decoding JSON from result.json")
            return

        write_deals(deals_dict)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a url")
    parser.add_argument(
        "--mode",
        default="find-deals",
        choices=["find-deals", "write-results"],
        help="Set the mode of the script",
    )
    parser.add_argument(
        "--address",
        default="https://www.manlydeck.com.au/",
        help="The URL to use to find deals",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)",
    )

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper())
    main(args.mode, args.address, log_level)
