"""SQS resource collector - queues."""

from __future__ import annotations

import logging

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class SQSCollector(BaseCollector):
    service_name = "sqs"

    def collect(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("list_queues")
        for page in paginator.paginate():
            for queue_url in page.get("QueueUrls", []):
                try:
                    attrs = self.client.get_queue_attributes(
                        QueueUrl=queue_url, AttributeNames=["All"]
                    )
                    attributes = attrs.get("Attributes", {})
                    queue_arn = attributes.get("QueueArn", "")
                    queue_name = queue_url.split("/")[-1]

                    resources.append(
                        Resource(
                            id=queue_arn or queue_url,
                            type=ResourceType.SQS_QUEUE,
                            name=queue_name,
                            region=self.region,
                            metadata={
                                "QueueUrl": queue_url,
                                "ApproximateNumberOfMessages": int(
                                    attributes.get("ApproximateNumberOfMessages", 0)
                                ),
                                "RedrivePolicy": attributes.get("RedrivePolicy"),
                            },
                        )
                    )
                except Exception as e:
                    logger.debug("Could not describe queue %s: %s", queue_url, e)
        return resources
