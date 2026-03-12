"""IAM resource collector - roles (global, opt-in)."""

from __future__ import annotations

import logging

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class IAMCollector(BaseCollector):
    service_name = "iam"
    is_global = True

    def collect(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("list_roles")
        for page in paginator.paginate():
            for role in page["Roles"]:
                # Skip AWS service-linked roles to reduce noise
                if "/aws-service-role/" in role.get("Path", ""):
                    continue

                resources.append(
                    Resource(
                        id=role["Arn"],
                        type=ResourceType.IAM_ROLE,
                        name=role["RoleName"],
                        region="global",
                        metadata={
                            "Path": role.get("Path"),
                            "CreateDate": role.get("CreateDate", "").isoformat()
                            if role.get("CreateDate")
                            else None,
                        },
                    )
                )
        return resources
