"""Route53 resource collector - hosted zones and records (global)."""

from __future__ import annotations

import logging

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class Route53Collector(BaseCollector):
    service_name = "route53"
    is_global = True

    def collect(self) -> list[Resource]:
        resources = []

        paginator = self.client.get_paginator("list_hosted_zones")
        for page in paginator.paginate():
            for zone in page["HostedZones"]:
                zone_id = zone["Id"].split("/")[-1]
                zone_name = zone["Name"].rstrip(".")

                # Collect records that point to AWS resources
                alias_targets = []
                try:
                    rec_paginator = self.client.get_paginator("list_resource_record_sets")
                    for rec_page in rec_paginator.paginate(HostedZoneId=zone_id):
                        for record in rec_page["ResourceRecordSets"]:
                            alias = record.get("AliasTarget")
                            if alias:
                                alias_targets.append(
                                    {
                                        "Name": record["Name"].rstrip("."),
                                        "Type": record["Type"],
                                        "DNSName": alias["DNSName"].rstrip("."),
                                    }
                                )
                except Exception:
                    pass

                resources.append(
                    Resource(
                        id=zone_id,
                        type=ResourceType.ROUTE53_ZONE,
                        name=zone_name,
                        region="global",
                        metadata={
                            "IsPrivate": zone.get("Config", {}).get("PrivateZone", False),
                            "RecordSetCount": zone.get("ResourceRecordSetCount", 0),
                            "AliasTargets": alias_targets,
                        },
                    )
                )
        return resources
