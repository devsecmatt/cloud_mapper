"""Base class for AWS service collectors."""

from __future__ import annotations

from abc import ABC, abstractmethod

import boto3

from cloud_mapper.discovery.models import Resource


class BaseCollector(ABC):
    """Abstract base class for all AWS service collectors."""

    service_name: str  # boto3 service name (e.g., "ec2", "rds")
    is_global: bool = False  # True for IAM, S3, Route53, CloudFront

    def __init__(self, session: boto3.Session, region: str):
        self.session = session
        self.region = region
        self.client = session.client(self.service_name, region_name=region)

    @abstractmethod
    def collect(self) -> list[Resource]:
        """Collect all resources of this service type.

        Returns a list of Resource dataclasses with metadata
        containing relationship IDs (VpcId, SubnetId, etc.).
        """
        ...

    def _get_name_tag(self, tags: list[dict] | None) -> str | None:
        """Extract the Name tag value from a list of AWS tags."""
        if not tags:
            return None
        for tag in tags:
            if tag.get("Key") == "Name":
                return tag.get("Value")
        return None
