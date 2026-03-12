"""SNS resource collector - topics and subscriptions."""

from __future__ import annotations

import logging

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class SNSCollector(BaseCollector):
    service_name = "sns"

    def collect(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("list_topics")
        for page in paginator.paginate():
            for topic in page["Topics"]:
                topic_arn = topic["TopicArn"]
                # Extract name from ARN
                topic_name = topic_arn.split(":")[-1]

                # Get subscriptions for this topic
                subscription_arns = []
                try:
                    sub_paginator = self.client.get_paginator("list_subscriptions_by_topic")
                    for sub_page in sub_paginator.paginate(TopicArn=topic_arn):
                        for sub in sub_page["Subscriptions"]:
                            endpoint = sub.get("Endpoint")
                            if endpoint:
                                subscription_arns.append(
                                    {
                                        "Protocol": sub.get("Protocol"),
                                        "Endpoint": endpoint,
                                    }
                                )
                except Exception:
                    pass

                resources.append(
                    Resource(
                        id=topic_arn,
                        type=ResourceType.SNS_TOPIC,
                        name=topic_name,
                        region=self.region,
                        metadata={
                            "Subscriptions": subscription_arns,
                        },
                    )
                )
        return resources
