"""Layout logic - groups resources into hierarchical clusters for the diagram."""

from __future__ import annotations

from collections import defaultdict

from cloud_mapper.discovery.models import ResourceGraph, ResourceType

# Resource types that appear inside VPCs
VPC_RESOURCE_TYPES = {
    ResourceType.SUBNET,
    ResourceType.EC2_INSTANCE,
    ResourceType.RDS_INSTANCE,
    ResourceType.RDS_CLUSTER,
    ResourceType.LOAD_BALANCER,
    ResourceType.NAT_GATEWAY,
    ResourceType.INTERNET_GATEWAY,
    ResourceType.SECURITY_GROUP,
    ResourceType.ECS_SERVICE,
    ResourceType.LAMBDA_FUNCTION,
}

# Resource types that are global (not region-specific)
GLOBAL_RESOURCE_TYPES = {
    ResourceType.S3_BUCKET,
    ResourceType.CLOUDFRONT_DISTRIBUTION,
    ResourceType.ROUTE53_ZONE,
    ResourceType.IAM_ROLE,
}

# Resource types to skip in diagrams (too noisy)
SKIP_IN_DIAGRAM = {
    ResourceType.SECURITY_GROUP,
    ResourceType.ROUTE_TABLE,
    ResourceType.TARGET_GROUP,
    ResourceType.ROUTE53_RECORD,
}


def group_by_region(graph: ResourceGraph) -> dict[str, list]:
    """Group resources by region. Returns {region: [resources]}."""
    regions = defaultdict(list)
    for resource in graph.resources.values():
        if resource.type in SKIP_IN_DIAGRAM:
            continue
        regions[resource.region].append(resource)
    return dict(regions)


def group_by_vpc(graph: ResourceGraph, region: str) -> tuple[dict, list]:
    """Group regional resources by VPC.

    Returns:
        (vpc_groups, standalone): where vpc_groups is {vpc_id: {subnet_id: [resources], '_vpc_level': [resources]}},
        and standalone is resources not in any VPC.
    """
    vpc_groups = defaultdict(lambda: defaultdict(list))
    standalone = []

    for resource in graph.resources.values():
        if resource.region != region:
            continue
        if resource.type in SKIP_IN_DIAGRAM:
            continue
        if resource.type == ResourceType.VPC:
            # VPCs themselves are cluster containers, not nodes
            continue
        if resource.type in GLOBAL_RESOURCE_TYPES:
            continue

        vpc_id = resource.metadata.get("VpcId")
        subnet_id = resource.metadata.get("SubnetId")

        if vpc_id:
            if subnet_id:
                vpc_groups[vpc_id][subnet_id].append(resource)
            else:
                vpc_groups[vpc_id]["_vpc_level"].append(resource)
        else:
            standalone.append(resource)

    return dict(vpc_groups), standalone


def get_global_resources(graph: ResourceGraph) -> list:
    """Get resources that should appear at the global (top) level."""
    return [
        r
        for r in graph.resources.values()
        if r.type in GLOBAL_RESOURCE_TYPES and r.type not in SKIP_IN_DIAGRAM
    ]
