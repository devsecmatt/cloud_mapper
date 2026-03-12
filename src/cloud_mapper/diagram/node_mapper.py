"""Maps ResourceType to diagrams library node classes."""

from __future__ import annotations

from cloud_mapper.discovery.models import ResourceType

# Lazy imports to avoid import errors when diagrams isn't installed
_NODE_MAP = None


def _get_node_map():
    global _NODE_MAP
    if _NODE_MAP is not None:
        return _NODE_MAP

    from diagrams.aws.compute import EC2, ECS, Lambda
    from diagrams.aws.database import RDS, Dynamodb
    from diagrams.aws.integration import SNS, SQS
    from diagrams.aws.network import (
        ALB,
        NLB,
        APIGateway,
        CloudFront,
        InternetGateway,
        NATGateway,
        Route53,
        VPC,
    )
    from diagrams.aws.security import IAMRole
    from diagrams.aws.storage import S3

    _NODE_MAP = {
        ResourceType.VPC: VPC,
        ResourceType.INTERNET_GATEWAY: InternetGateway,
        ResourceType.NAT_GATEWAY: NATGateway,
        ResourceType.EC2_INSTANCE: EC2,
        ResourceType.LAMBDA_FUNCTION: Lambda,
        ResourceType.ECS_CLUSTER: ECS,
        ResourceType.ECS_SERVICE: ECS,
        ResourceType.LOAD_BALANCER: ALB,  # Default; overridden for NLB
        ResourceType.RDS_INSTANCE: RDS,
        ResourceType.RDS_CLUSTER: RDS,
        ResourceType.DYNAMODB_TABLE: Dynamodb,
        ResourceType.S3_BUCKET: S3,
        ResourceType.SNS_TOPIC: SNS,
        ResourceType.SQS_QUEUE: SQS,
        ResourceType.API_GATEWAY: APIGateway,
        ResourceType.ROUTE53_ZONE: Route53,
        ResourceType.CLOUDFRONT_DISTRIBUTION: CloudFront,
        ResourceType.IAM_ROLE: IAMRole,
    }
    return _NODE_MAP


def get_node_class(resource_type: ResourceType, metadata: dict | None = None):
    """Get the diagrams node class for a resource type."""
    node_map = _get_node_map()

    # Special case: NLB vs ALB
    if resource_type == ResourceType.LOAD_BALANCER and metadata:
        lb_type = metadata.get("Type", "application")
        if lb_type == "network":
            from diagrams.aws.network import NLB

            return NLB

    return node_map.get(resource_type)


def create_node(resource):
    """Create a diagrams node from a Resource. Returns (node, label) or None."""
    node_class = get_node_class(resource.type, resource.metadata)
    if node_class is None:
        return None

    label = resource.name
    if len(label) > 30:
        label = label[:27] + "..."

    return node_class(label)
