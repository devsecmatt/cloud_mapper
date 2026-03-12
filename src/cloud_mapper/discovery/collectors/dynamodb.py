"""DynamoDB resource collector - tables."""

from __future__ import annotations

import logging

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class DynamoDBCollector(BaseCollector):
    service_name = "dynamodb"

    def collect(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("list_tables")
        for page in paginator.paginate():
            for table_name in page["TableNames"]:
                try:
                    response = self.client.describe_table(TableName=table_name)
                    table = response["Table"]
                    resources.append(
                        Resource(
                            id=table["TableArn"],
                            type=ResourceType.DYNAMODB_TABLE,
                            name=table_name,
                            region=self.region,
                            metadata={
                                "TableStatus": table.get("TableStatus"),
                                "ItemCount": table.get("ItemCount", 0),
                                "TableSizeBytes": table.get("TableSizeBytes", 0),
                            },
                        )
                    )
                except Exception as e:
                    logger.debug("Could not describe table %s: %s", table_name, e)
        return resources
