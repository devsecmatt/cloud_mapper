"""CloudFront resource collector - distributions (global)."""

from __future__ import annotations

import logging

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class CloudFrontCollector(BaseCollector):
    service_name = "cloudfront"
    is_global = True

    def collect(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("list_distributions")
        for page in paginator.paginate():
            distribution_list = page.get("DistributionList", {})
            for dist in distribution_list.get("Items", []):
                origins = []
                for origin in dist.get("Origins", {}).get("Items", []):
                    origins.append(
                        {
                            "DomainName": origin.get("DomainName"),
                            "Id": origin.get("Id"),
                            "S3OriginConfig": bool(origin.get("S3OriginConfig")),
                        }
                    )

                resources.append(
                    Resource(
                        id=dist["Id"],
                        type=ResourceType.CLOUDFRONT_DISTRIBUTION,
                        name=dist.get("DomainName", dist["Id"]),
                        region="global",
                        metadata={
                            "DomainName": dist.get("DomainName"),
                            "Status": dist.get("Status"),
                            "Origins": origins,
                            "Aliases": dist.get("Aliases", {}).get("Items", []),
                        },
                    )
                )
        return resources
