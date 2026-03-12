"""EC2 resource collector - instances and security groups."""

from __future__ import annotations

import logging

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class EC2Collector(BaseCollector):
    service_name = "ec2"

    def collect(self) -> list[Resource]:
        resources = []
        resources.extend(self._collect_instances())
        resources.extend(self._collect_security_groups())
        return resources

    def _collect_instances(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("describe_instances")
        for page in paginator.paginate():
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    # Skip terminated instances
                    if instance["State"]["Name"] == "terminated":
                        continue

                    name = self._get_name_tag(instance.get("Tags")) or instance["InstanceId"]
                    sg_ids = [sg["GroupId"] for sg in instance.get("SecurityGroups", [])]

                    resources.append(
                        Resource(
                            id=instance["InstanceId"],
                            type=ResourceType.EC2_INSTANCE,
                            name=name,
                            region=self.region,
                            metadata={
                                "InstanceType": instance.get("InstanceType"),
                                "State": instance["State"]["Name"],
                                "VpcId": instance.get("VpcId"),
                                "SubnetId": instance.get("SubnetId"),
                                "SecurityGroupIds": sg_ids,
                                "PrivateIpAddress": instance.get("PrivateIpAddress"),
                                "PublicIpAddress": instance.get("PublicIpAddress"),
                            },
                        )
                    )
        return resources

    def _collect_security_groups(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("describe_security_groups")
        for page in paginator.paginate():
            for sg in page["SecurityGroups"]:
                resources.append(
                    Resource(
                        id=sg["GroupId"],
                        type=ResourceType.SECURITY_GROUP,
                        name=sg.get("GroupName", sg["GroupId"]),
                        region=self.region,
                        metadata={
                            "VpcId": sg.get("VpcId"),
                            "Description": sg.get("Description"),
                        },
                    )
                )
        return resources
