"""Data models for AWS resource discovery."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResourceType(Enum):
    # Networking
    VPC = "vpc"
    SUBNET = "subnet"
    INTERNET_GATEWAY = "internet_gateway"
    NAT_GATEWAY = "nat_gateway"
    ROUTE_TABLE = "route_table"

    # Compute
    EC2_INSTANCE = "ec2_instance"
    SECURITY_GROUP = "security_group"
    LAMBDA_FUNCTION = "lambda_function"
    ECS_CLUSTER = "ecs_cluster"
    ECS_SERVICE = "ecs_service"

    # Load Balancing
    LOAD_BALANCER = "load_balancer"
    TARGET_GROUP = "target_group"

    # Databases
    RDS_INSTANCE = "rds_instance"
    RDS_CLUSTER = "rds_cluster"
    DYNAMODB_TABLE = "dynamodb_table"

    # Storage
    S3_BUCKET = "s3_bucket"

    # Integration
    SNS_TOPIC = "sns_topic"
    SQS_QUEUE = "sqs_queue"

    # API
    API_GATEWAY = "api_gateway"

    # DNS & CDN
    ROUTE53_ZONE = "route53_zone"
    ROUTE53_RECORD = "route53_record"
    CLOUDFRONT_DISTRIBUTION = "cloudfront_distribution"

    # Identity
    IAM_ROLE = "iam_role"


@dataclass
class Resource:
    """A single AWS resource."""

    id: str
    type: ResourceType
    name: str
    region: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "region": self.region,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Resource:
        return cls(
            id=data["id"],
            type=ResourceType(data["type"]),
            name=data["name"],
            region=data["region"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class Relationship:
    """A directed relationship between two resources."""

    source_id: str
    target_id: str
    relation_type: str  # "contains", "routes_to", "triggers", "targets", "attached_to"

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Relationship:
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=data["relation_type"],
        )


@dataclass
class ResourceGraph:
    """Graph of AWS resources and their relationships."""

    resources: dict[str, Resource] = field(default_factory=dict)
    relationships: list[Relationship] = field(default_factory=list)

    def add_resource(self, resource: Resource) -> None:
        self.resources[resource.id] = resource

    def add_relationship(self, source_id: str, target_id: str, relation_type: str) -> None:
        self.relationships.append(Relationship(source_id, target_id, relation_type))

    def get_resources_by_type(self, rtype: ResourceType) -> list[Resource]:
        return [r for r in self.resources.values() if r.type == rtype]

    def get_children(self, parent_id: str, relation_type: str = "contains") -> list[Resource]:
        """Get resources that are contained by the given parent."""
        child_ids = [
            rel.target_id
            for rel in self.relationships
            if rel.source_id == parent_id and rel.relation_type == relation_type
        ]
        return [self.resources[cid] for cid in child_ids if cid in self.resources]

    def get_related(self, resource_id: str) -> list[tuple[Resource, str]]:
        """Get all resources related to the given resource, with relationship types."""
        results = []
        for rel in self.relationships:
            if rel.source_id == resource_id and rel.target_id in self.resources:
                results.append((self.resources[rel.target_id], rel.relation_type))
            elif rel.target_id == resource_id and rel.source_id in self.resources:
                results.append((self.resources[rel.source_id], rel.relation_type))
        return results

    def filter_by_vpc(self, vpc_id: str) -> ResourceGraph:
        """Return a new graph containing only resources in the specified VPC."""
        filtered = ResourceGraph()

        # Always include the VPC itself
        if vpc_id in self.resources:
            filtered.add_resource(self.resources[vpc_id])

        # Find all resource IDs that belong to this VPC
        vpc_resource_ids = {vpc_id}
        for resource in self.resources.values():
            if resource.metadata.get("VpcId") == vpc_id:
                vpc_resource_ids.add(resource.id)
                filtered.add_resource(resource)

        # Also include resources contained by VPC resources (transitive)
        for rel in self.relationships:
            if rel.source_id in vpc_resource_ids and rel.target_id in self.resources:
                target = self.resources[rel.target_id]
                vpc_resource_ids.add(target.id)
                filtered.add_resource(target)

        # Copy relevant relationships
        for rel in self.relationships:
            if rel.source_id in vpc_resource_ids and rel.target_id in vpc_resource_ids:
                filtered.relationships.append(rel)

        return filtered

    def merge(self, other: ResourceGraph) -> None:
        """Merge another graph into this one."""
        for resource in other.resources.values():
            self.add_resource(resource)
        self.relationships.extend(other.relationships)

    def print_summary(self, console) -> None:
        """Print a summary table of discovered resources."""
        from rich.table import Table

        counts = Counter(r.type.value for r in self.resources.values())
        if not counts:
            console.print("[yellow]No resources found.[/yellow]")
            return

        table = Table(title="Resource Summary")
        table.add_column("Resource Type", style="cyan")
        table.add_column("Count", style="green", justify="right")

        for rtype, count in sorted(counts.items()):
            table.add_row(rtype, str(count))

        table.add_row("[bold]Total[/bold]", f"[bold]{sum(counts.values())}[/bold]")
        console.print(table)

    def to_dict(self) -> dict:
        return {
            "resources": [r.to_dict() for r in self.resources.values()],
            "relationships": [r.to_dict() for r in self.relationships],
        }

    @classmethod
    def from_dict(cls, data: dict) -> ResourceGraph:
        graph = cls()
        for r in data["resources"]:
            graph.add_resource(Resource.from_dict(r))
        for r in data["relationships"]:
            graph.relationships.append(Relationship.from_dict(r))
        return graph

    def to_json_file(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_json_file(cls, path: str) -> ResourceGraph:
        with open(path) as f:
            return cls.from_dict(json.load(f))
