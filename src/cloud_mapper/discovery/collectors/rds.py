"""RDS resource collector - instances and clusters."""

from __future__ import annotations

import logging

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class RDSCollector(BaseCollector):
    service_name = "rds"

    def collect(self) -> list[Resource]:
        resources = []
        resources.extend(self._collect_instances())
        resources.extend(self._collect_clusters())
        return resources

    def _collect_instances(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for db in page["DBInstances"]:
                subnet_group = db.get("DBSubnetGroup", {})
                vpc_id = subnet_group.get("VpcId")
                subnet_ids = [
                    s["SubnetIdentifier"]
                    for s in subnet_group.get("Subnets", [])
                ]

                resources.append(
                    Resource(
                        id=db["DBInstanceIdentifier"],
                        type=ResourceType.RDS_INSTANCE,
                        name=db["DBInstanceIdentifier"],
                        region=self.region,
                        metadata={
                            "Engine": db.get("Engine"),
                            "EngineVersion": db.get("EngineVersion"),
                            "DBInstanceClass": db.get("DBInstanceClass"),
                            "VpcId": vpc_id,
                            "SubnetIds": subnet_ids,
                            "MultiAZ": db.get("MultiAZ", False),
                            "DBClusterIdentifier": db.get("DBClusterIdentifier"),
                            "SecurityGroupIds": [
                                sg["VpcSecurityGroupId"]
                                for sg in db.get("VpcSecurityGroups", [])
                            ],
                        },
                    )
                )
        return resources

    def _collect_clusters(self) -> list[Resource]:
        resources = []
        paginator = self.client.get_paginator("describe_db_clusters")
        for page in paginator.paginate():
            for cluster in page["DBClusters"]:
                member_ids = [
                    m["DBInstanceIdentifier"] for m in cluster.get("DBClusterMembers", [])
                ]
                resources.append(
                    Resource(
                        id=cluster["DBClusterIdentifier"],
                        type=ResourceType.RDS_CLUSTER,
                        name=cluster["DBClusterIdentifier"],
                        region=self.region,
                        metadata={
                            "Engine": cluster.get("Engine"),
                            "MemberInstanceIds": member_ids,
                            "SecurityGroupIds": [
                                sg["VpcSecurityGroupId"]
                                for sg in cluster.get("VpcSecurityGroups", [])
                            ],
                        },
                    )
                )
        return resources
