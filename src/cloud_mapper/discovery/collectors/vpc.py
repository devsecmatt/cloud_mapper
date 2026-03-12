"""VPC resource collector - VPCs, subnets, internet gateways, NAT gateways."""

from __future__ import annotations

import logging

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class VPCCollector(BaseCollector):
    service_name = "ec2"

    def collect(self) -> list[Resource]:
        resources = []
        resources.extend(self._collect_vpcs())
        resources.extend(self._collect_subnets())
        resources.extend(self._collect_internet_gateways())
        resources.extend(self._collect_nat_gateways())
        return resources

    def _collect_vpcs(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("describe_vpcs")
        for page in paginator.paginate():
            for vpc in page["Vpcs"]:
                name = self._get_name_tag(vpc.get("Tags")) or vpc["VpcId"]
                resources.append(
                    Resource(
                        id=vpc["VpcId"],
                        type=ResourceType.VPC,
                        name=name,
                        region=self.region,
                        metadata={
                            "CidrBlock": vpc["CidrBlock"],
                            "IsDefault": vpc.get("IsDefault", False),
                            "State": vpc["State"],
                        },
                    )
                )
        return resources

    def _collect_subnets(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("describe_subnets")
        for page in paginator.paginate():
            for subnet in page["Subnets"]:
                name = self._get_name_tag(subnet.get("Tags")) or subnet["SubnetId"]
                resources.append(
                    Resource(
                        id=subnet["SubnetId"],
                        type=ResourceType.SUBNET,
                        name=name,
                        region=self.region,
                        metadata={
                            "VpcId": subnet["VpcId"],
                            "CidrBlock": subnet["CidrBlock"],
                            "AvailabilityZone": subnet["AvailabilityZone"],
                            "MapPublicIpOnLaunch": subnet.get("MapPublicIpOnLaunch", False),
                        },
                    )
                )
        return resources

    def _collect_internet_gateways(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("describe_internet_gateways")
        for page in paginator.paginate():
            for igw in page["InternetGateways"]:
                name = self._get_name_tag(igw.get("Tags")) or igw["InternetGatewayId"]
                vpc_ids = [a["VpcId"] for a in igw.get("Attachments", []) if a.get("VpcId")]
                resources.append(
                    Resource(
                        id=igw["InternetGatewayId"],
                        type=ResourceType.INTERNET_GATEWAY,
                        name=name,
                        region=self.region,
                        metadata={"VpcIds": vpc_ids},
                    )
                )
        return resources

    def _collect_nat_gateways(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("describe_nat_gateways")
        for page in paginator.paginate(
            Filters=[{"Name": "state", "Values": ["available", "pending"]}]
        ):
            for nat in page["NatGateways"]:
                name = self._get_name_tag(nat.get("Tags")) or nat["NatGatewayId"]
                resources.append(
                    Resource(
                        id=nat["NatGatewayId"],
                        type=ResourceType.NAT_GATEWAY,
                        name=name,
                        region=self.region,
                        metadata={
                            "VpcId": nat.get("VpcId"),
                            "SubnetId": nat.get("SubnetId"),
                        },
                    )
                )
        return resources
