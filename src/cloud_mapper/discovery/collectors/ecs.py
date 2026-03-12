"""ECS resource collector - clusters and services."""

from __future__ import annotations

import logging

import botocore.exceptions

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class ECSCollector(BaseCollector):
    service_name = "ecs"

    def collect(self) -> list[Resource]:
        resources = []

        # List all clusters
        cluster_arns = []
        paginator = self.client.get_paginator("list_clusters")
        for page in paginator.paginate():
            cluster_arns.extend(page["clusterArns"])

        if not cluster_arns:
            return resources

        # Describe clusters in batches of 100
        for i in range(0, len(cluster_arns), 100):
            batch = cluster_arns[i : i + 100]
            response = self.client.describe_clusters(clusters=batch)
            for cluster in response.get("clusters", []):
                resources.append(
                    Resource(
                        id=cluster["clusterArn"],
                        type=ResourceType.ECS_CLUSTER,
                        name=cluster["clusterName"],
                        region=self.region,
                        metadata={
                            "Status": cluster.get("status"),
                            "RunningTasksCount": cluster.get("runningTasksCount", 0),
                            "ActiveServicesCount": cluster.get("activeServicesCount", 0),
                        },
                    )
                )

                # List services in this cluster
                resources.extend(self._collect_services(cluster["clusterArn"]))

        return resources

    def _collect_services(self, cluster_arn: str) -> list[Resource]:
        resources = []
        try:
            service_arns = []
            paginator = self.client.get_paginator("list_services")
            for page in paginator.paginate(cluster=cluster_arn):
                service_arns.extend(page["serviceArns"])

            if not service_arns:
                return resources

            for i in range(0, len(service_arns), 10):
                batch = service_arns[i : i + 10]
                response = self.client.describe_services(cluster=cluster_arn, services=batch)
                for svc in response.get("services", []):
                    lb_info = []
                    for lb in svc.get("loadBalancers", []):
                        lb_info.append(
                            {
                                "targetGroupArn": lb.get("targetGroupArn"),
                                "containerName": lb.get("containerName"),
                                "containerPort": lb.get("containerPort"),
                            }
                        )

                    network_config = svc.get("networkConfiguration", {}).get(
                        "awsvpcConfiguration", {}
                    )

                    resources.append(
                        Resource(
                            id=svc["serviceArn"],
                            type=ResourceType.ECS_SERVICE,
                            name=svc["serviceName"],
                            region=self.region,
                            metadata={
                                "ClusterArn": cluster_arn,
                                "Status": svc.get("status"),
                                "DesiredCount": svc.get("desiredCount", 0),
                                "RunningCount": svc.get("runningCount", 0),
                                "LoadBalancers": lb_info,
                                "SubnetIds": network_config.get("subnets", []),
                                "SecurityGroupIds": network_config.get("securityGroups", []),
                                "VpcId": None,  # Resolved via subnets in coordinator
                            },
                        )
                    )
        except botocore.exceptions.ClientError as e:
            logger.debug("Could not list services for cluster %s: %s", cluster_arn, e)
        return resources
