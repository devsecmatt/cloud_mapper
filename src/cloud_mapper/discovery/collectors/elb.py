"""ELB resource collector - ALB, NLB, CLB, and target groups."""

from __future__ import annotations

import logging

import botocore.exceptions

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class ELBCollector(BaseCollector):
    service_name = "elbv2"

    def collect(self) -> list[Resource]:
        resources = []
        resources.extend(self._collect_v2_load_balancers())
        resources.extend(self._collect_classic_load_balancers())
        return resources

    def _collect_v2_load_balancers(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("describe_load_balancers")
        for page in paginator.paginate():
            for lb in page["LoadBalancers"]:
                subnet_ids = [az["SubnetId"] for az in lb.get("AvailabilityZones", []) if az.get("SubnetId")]

                # Collect target groups for this LB
                target_instance_ids = []
                try:
                    tg_response = self.client.describe_target_groups(
                        LoadBalancerArn=lb["LoadBalancerArn"]
                    )
                    for tg in tg_response.get("TargetGroups", []):
                        try:
                            health = self.client.describe_target_health(
                                TargetGroupArn=tg["TargetGroupArn"]
                            )
                            for desc in health.get("TargetHealthDescriptions", []):
                                target_id = desc["Target"]["Id"]
                                target_instance_ids.append(target_id)
                        except botocore.exceptions.ClientError:
                            pass
                except botocore.exceptions.ClientError:
                    pass

                resources.append(
                    Resource(
                        id=lb["LoadBalancerArn"],
                        type=ResourceType.LOAD_BALANCER,
                        name=lb["LoadBalancerName"],
                        region=self.region,
                        metadata={
                            "VpcId": lb.get("VpcId"),
                            "Type": lb.get("Type", "application"),
                            "Scheme": lb.get("Scheme"),
                            "SubnetIds": subnet_ids,
                            "TargetInstanceIds": target_instance_ids,
                            "DNSName": lb.get("DNSName"),
                        },
                    )
                )
        return resources

    def _collect_classic_load_balancers(self) -> list[Resource]:
        resources = []
        try:
            elb_client = self.session.client("elb", region_name=self.region)
            paginator = elb_client.get_paginator("describe_load_balancers")
            for page in paginator.paginate():
                for lb in page["LoadBalancerDescriptions"]:
                    instance_ids = [i["InstanceId"] for i in lb.get("Instances", [])]
                    resources.append(
                        Resource(
                            id=lb["LoadBalancerName"],
                            type=ResourceType.LOAD_BALANCER,
                            name=lb["LoadBalancerName"],
                            region=self.region,
                            metadata={
                                "VpcId": lb.get("VPCId"),
                                "Type": "classic",
                                "Scheme": lb.get("Scheme"),
                                "SubnetIds": lb.get("Subnets", []),
                                "TargetInstanceIds": instance_ids,
                                "DNSName": lb.get("DNSName"),
                            },
                        )
                    )
        except botocore.exceptions.ClientError as e:
            logger.debug("Could not list classic load balancers: %s", e)
        return resources
