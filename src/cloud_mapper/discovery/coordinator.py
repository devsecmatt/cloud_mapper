"""Discovery coordinator - orchestrates all collectors across regions."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import botocore.exceptions
from rich.progress import Progress, SpinnerColumn, TextColumn

from cloud_mapper.config import DEFAULT_MAX_WORKERS, GLOBAL_REGION, GLOBAL_SERVICES
from cloud_mapper.discovery.collectors import COLLECTOR_MAP
from cloud_mapper.discovery.models import ResourceGraph, ResourceType

logger = logging.getLogger(__name__)


class DiscoveryCoordinator:
    """Orchestrates AWS resource discovery across services and regions."""

    def __init__(
        self,
        session,
        regions: list[str],
        services: list[str],
        max_workers: int = DEFAULT_MAX_WORKERS,
    ):
        self.session = session
        self.regions = regions
        self.services = services
        self.max_workers = max_workers

    def discover_all(self) -> ResourceGraph:
        """Run all collectors across all regions and build a unified resource graph."""
        graph = ResourceGraph()

        # Separate global vs regional services
        global_services = [s for s in self.services if s in GLOBAL_SERVICES]
        regional_services = [s for s in self.services if s not in GLOBAL_SERVICES]

        # Build list of (service, region) work items
        work_items = []
        for service in global_services:
            work_items.append((service, GLOBAL_REGION))
        for region in self.regions:
            for service in regional_services:
                work_items.append((service, region))

        # Execute collectors with thread pool and progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Discovering resources...", total=len(work_items))

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {}
                for service, region in work_items:
                    future = executor.submit(self._run_collector, service, region)
                    futures[future] = (service, region)

                for future in as_completed(futures):
                    service, region = futures[future]
                    progress.update(task, advance=1, description=f"Scanning {service} in {region}")
                    try:
                        resources = future.result()
                        for resource in resources:
                            graph.add_resource(resource)
                    except Exception as e:
                        logger.error("Failed to collect %s in %s: %s", service, region, e)

        # Build relationships from metadata
        self._resolve_relationships(graph)

        return graph

    def _run_collector(self, service: str, region: str) -> list:
        """Run a single collector, handling permission errors gracefully."""
        collector_class = COLLECTOR_MAP.get(service)
        if not collector_class:
            logger.warning("No collector for service: %s", service)
            return []

        try:
            collector = collector_class(self.session, region)
            return collector.collect()
        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in (
                "AccessDenied",
                "UnauthorizedAccess",
                "AccessDeniedException",
                "AuthorizationError",
            ):
                logger.warning("No permission for %s in %s, skipping", service, region)
                return []
            raise

    def _resolve_relationships(self, graph: ResourceGraph) -> None:
        """Scan resource metadata to build relationships between resources."""
        resource_ids = set(graph.resources.keys())

        for resource in list(graph.resources.values()):
            meta = resource.metadata

            # VPC containment: subnets, instances, RDS, etc.
            if resource.type == ResourceType.SUBNET:
                vpc_id = meta.get("VpcId")
                if vpc_id and vpc_id in resource_ids:
                    graph.add_relationship(vpc_id, resource.id, "contains")

            elif resource.type == ResourceType.EC2_INSTANCE:
                subnet_id = meta.get("SubnetId")
                if subnet_id and subnet_id in resource_ids:
                    graph.add_relationship(subnet_id, resource.id, "contains")

            elif resource.type == ResourceType.NAT_GATEWAY:
                subnet_id = meta.get("SubnetId")
                if subnet_id and subnet_id in resource_ids:
                    graph.add_relationship(subnet_id, resource.id, "contains")

            elif resource.type == ResourceType.INTERNET_GATEWAY:
                for vpc_id in meta.get("VpcIds", []):
                    if vpc_id in resource_ids:
                        graph.add_relationship(vpc_id, resource.id, "attached_to")

            elif resource.type == ResourceType.SECURITY_GROUP:
                vpc_id = meta.get("VpcId")
                if vpc_id and vpc_id in resource_ids:
                    graph.add_relationship(vpc_id, resource.id, "contains")

            # Load balancer -> target instances
            elif resource.type == ResourceType.LOAD_BALANCER:
                vpc_id = meta.get("VpcId")
                if vpc_id and vpc_id in resource_ids:
                    graph.add_relationship(vpc_id, resource.id, "contains")
                for target_id in meta.get("TargetInstanceIds", []):
                    if target_id in resource_ids:
                        graph.add_relationship(resource.id, target_id, "routes_to")

            # RDS in VPC
            elif resource.type == ResourceType.RDS_INSTANCE:
                vpc_id = meta.get("VpcId")
                if vpc_id and vpc_id in resource_ids:
                    graph.add_relationship(vpc_id, resource.id, "contains")
                cluster_id = meta.get("DBClusterIdentifier")
                if cluster_id and cluster_id in resource_ids:
                    graph.add_relationship(cluster_id, resource.id, "contains")

            # Lambda in VPC
            elif resource.type == ResourceType.LAMBDA_FUNCTION:
                vpc_id = meta.get("VpcId")
                if vpc_id and vpc_id in resource_ids:
                    graph.add_relationship(vpc_id, resource.id, "contains")
                # Event source triggers
                for source_arn in meta.get("EventSourceArns", []):
                    if source_arn and source_arn in resource_ids:
                        graph.add_relationship(source_arn, resource.id, "triggers")

            # ECS service in cluster
            elif resource.type == ResourceType.ECS_SERVICE:
                cluster_arn = meta.get("ClusterArn")
                if cluster_arn and cluster_arn in resource_ids:
                    graph.add_relationship(cluster_arn, resource.id, "contains")

            # SNS -> subscription endpoints (SQS, Lambda)
            elif resource.type == ResourceType.SNS_TOPIC:
                for sub in meta.get("Subscriptions", []):
                    endpoint = sub.get("Endpoint")
                    if endpoint and endpoint in resource_ids:
                        graph.add_relationship(resource.id, endpoint, "triggers")

            # CloudFront -> origins (S3 buckets, LBs)
            elif resource.type == ResourceType.CLOUDFRONT_DISTRIBUTION:
                for origin in meta.get("Origins", []):
                    domain = origin.get("DomainName", "")
                    # Try to match S3 bucket origins
                    if ".s3." in domain or domain.endswith(".s3.amazonaws.com"):
                        bucket_name = domain.split(".s3")[0]
                        if bucket_name in resource_ids:
                            graph.add_relationship(resource.id, bucket_name, "routes_to")

            # Route53 alias targets -> LBs, CloudFront, etc.
            elif resource.type == ResourceType.ROUTE53_ZONE:
                for alias in meta.get("AliasTargets", []):
                    dns_name = alias.get("DNSName", "")
                    # Try to match LB DNS names
                    for r in graph.resources.values():
                        if r.type == ResourceType.LOAD_BALANCER:
                            if r.metadata.get("DNSName") and dns_name.startswith(
                                r.metadata["DNSName"]
                            ):
                                graph.add_relationship(resource.id, r.id, "routes_to")
                        elif r.type == ResourceType.CLOUDFRONT_DISTRIBUTION:
                            if r.metadata.get("DomainName") and dns_name.startswith(
                                r.metadata["DomainName"]
                            ):
                                graph.add_relationship(resource.id, r.id, "routes_to")
