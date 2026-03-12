"""S3 resource collector - buckets (global)."""

from __future__ import annotations

import logging

import botocore.exceptions

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class S3Collector(BaseCollector):
    service_name = "s3"
    is_global = True

    def collect(self) -> list[Resource]:
        resources = []
        response = self.client.list_buckets()

        for bucket in response.get("Buckets", []):
            bucket_name = bucket["Name"]

            # Get bucket location
            try:
                loc = self.client.get_bucket_location(Bucket=bucket_name)
                region = loc.get("LocationConstraint") or "us-east-1"
            except botocore.exceptions.ClientError:
                region = "unknown"

            resources.append(
                Resource(
                    id=bucket_name,
                    type=ResourceType.S3_BUCKET,
                    name=bucket_name,
                    region=region,
                    metadata={
                        "CreationDate": bucket.get("CreationDate", "").isoformat()
                        if bucket.get("CreationDate")
                        else None,
                    },
                )
            )
        return resources
