"""Lambda resource collector - functions and event source mappings."""

from __future__ import annotations

import logging

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class LambdaCollector(BaseCollector):
    service_name = "lambda"

    def collect(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("list_functions")
        for page in paginator.paginate():
            for func in page["Functions"]:
                vpc_config = func.get("VpcConfig", {})
                vpc_id = vpc_config.get("VpcId") or None
                subnet_ids = vpc_config.get("SubnetIds", [])
                sg_ids = vpc_config.get("SecurityGroupIds", [])

                # Get event source mappings for this function
                event_sources = []
                try:
                    esm_paginator = self.client.get_paginator("list_event_source_mappings")
                    for esm_page in esm_paginator.paginate(FunctionName=func["FunctionArn"]):
                        for esm in esm_page["EventSourceMappings"]:
                            event_sources.append(esm.get("EventSourceArn"))
                except Exception:
                    pass

                resources.append(
                    Resource(
                        id=func["FunctionArn"],
                        type=ResourceType.LAMBDA_FUNCTION,
                        name=func["FunctionName"],
                        region=self.region,
                        metadata={
                            "Runtime": func.get("Runtime"),
                            "MemorySize": func.get("MemorySize"),
                            "Timeout": func.get("Timeout"),
                            "VpcId": vpc_id,
                            "SubnetIds": subnet_ids,
                            "SecurityGroupIds": sg_ids,
                            "EventSourceArns": event_sources,
                        },
                    )
                )
        return resources
