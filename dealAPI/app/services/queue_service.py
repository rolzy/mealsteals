import json
import os
import uuid as uuid_pkg
from datetime import UTC, datetime
from typing import Optional

import boto3

from ..core.logging import get_logger

logger = get_logger(__name__)


class QueueService:
    """Service for managing async job queues"""

    def __init__(self):
        self.sqs = None
        self.queue_url = os.getenv("DEAL_SCRAPING_QUEUE_URL")
        self.sqs = boto3.client("sqs")

    async def queue_deal_scraping_job(
        self, restaurant_id: uuid_pkg.UUID, restaurant_url: str
    ) -> Optional[str]:
        """
        Queue a deal scraping job for a restaurant

        Args:
            restaurant_id: UUID of the restaurant
            restaurant_url: URL of the restaurant website to scrape

        Returns:
            Message ID if successful, None if failed
        """
        logger.info(f"Queueing deal scraping job for restaurant {restaurant_id}")

        message = {
            "restaurant_id": str(restaurant_id),
            "url": restaurant_url,
            "timestamp": datetime.now(UTC).isoformat(),
            "job_type": "deal_scraping",
        }

        try:
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    "restaurant_id": {
                        "StringValue": str(restaurant_id),
                        "DataType": "String",
                    },
                    "job_type": {
                        "StringValue": "deal_scraping",
                        "DataType": "String",
                    },
                },
            )
            message_id = response.get("MessageId")
            logger.info(
                f"Successfully queued deal scraping job for restaurant {restaurant_id}, message ID: {message_id}"
            )
            return message_id

        except Exception as e:
            logger.error(
                f"Failed to queue deal scraping job for restaurant {restaurant_id}: {str(e)}"
            )
            # Don't fail the main operation if queueing fails
            return None

    def get_job_status(self, job_id: str) -> dict:
        """
        Get the status of a queued job (placeholder for future implementation)

        Args:
            job_id: ID of the job to check

        Returns:
            Job status information
        """
        # This would typically check a status table or cache
        # For now, return a placeholder
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Job status tracking not yet implemented",
        }
