"""Main diagram renderer - generates AWS architecture diagrams."""

from __future__ import annotations

import logging

from diagrams import Cluster, Diagram, Edge

from cloud_mapper.diagram.edge_builder import build_edges
from cloud_mapper.diagram.layout import get_global_resources, group_by_region, group_by_vpc
from cloud_mapper.diagram.node_mapper import create_node
from cloud_mapper.discovery.models import ResourceGraph, ResourceType

logger = logging.getLogger(__name__)


class DiagramRenderer:
    """Renders a ResourceGraph as an architecture diagram."""

    def __init__(self, graph: ResourceGraph, output_path: str, output_format: str = "png"):
        self.graph = graph
        self.output_path = output_path
        self.output_format = output_format
        self.node_refs: dict[str, object] = {}

    def render(self) -> str:
        """Render the diagram and return the output file path."""
        regions = group_by_region(self.graph)
        global_resources = get_global_resources(self.graph)

        # Remove 'global' from regions since we handle it separately
        regions.pop("global", None)

        with Diagram(
            "AWS Architecture",
            filename=self.output_path,
            outformat=self.output_format,
            show=False,
            direction="TB",
            graph_attr={
                "fontsize": "16",
                "bgcolor": "white",
                "pad": "0.5",
                "nodesep": "0.8",
                "ranksep": "1.0",
            },
        ):
            # Render global resources outside any region cluster
            if global_resources:
                with Cluster("Global Services", graph_attr={"style": "dashed", "color": "#666666"}):
                    self._render_resources(global_resources)

            # Render each region
            for region in sorted(regions.keys()):
                self._render_region(region)

            # Draw edges
            edges = build_edges(self.graph, self.node_refs)
            for source, target, style in edges:
                source >> Edge(
                    style=style.get("style", "solid"),
                    color=style.get("color", "#333333"),
                ) >> target

        output_file = f"{self.output_path}.{self.output_format}"
        return output_file

    def _render_region(self, region: str) -> None:
        """Render all resources in a region."""
        vpc_groups, standalone = group_by_vpc(self.graph, region)

        with Cluster(f"Region: {region}", graph_attr={"style": "rounded", "color": "#FF9900"}):
            # Render standalone resources (not in any VPC)
            if standalone:
                self._render_resources(standalone)

            # Render each VPC
            for vpc_id, subnet_groups in vpc_groups.items():
                vpc = self.graph.resources.get(vpc_id)
                vpc_label = f"VPC: {vpc.name}" if vpc else f"VPC: {vpc_id}"
                cidr = vpc.metadata.get("CidrBlock", "") if vpc else ""
                if cidr:
                    vpc_label += f"\n({cidr})"

                with Cluster(vpc_label, graph_attr={"style": "rounded", "color": "#3B48CC"}):
                    # VPC-level resources (not in a specific subnet)
                    vpc_level = subnet_groups.pop("_vpc_level", [])
                    if vpc_level:
                        self._render_resources(vpc_level)

                    # Render each subnet
                    for subnet_id, resources in subnet_groups.items():
                        subnet = self.graph.resources.get(subnet_id)
                        if subnet:
                            is_public = subnet.metadata.get("MapPublicIpOnLaunch", False)
                            az = subnet.metadata.get("AvailabilityZone", "")
                            subnet_label = f"{subnet.name}"
                            if az:
                                subnet_label += f"\n({az})"
                            color = "#2E8B57" if is_public else "#4A708B"
                        else:
                            subnet_label = subnet_id
                            color = "#4A708B"

                        with Cluster(
                            subnet_label, graph_attr={"style": "rounded", "color": color}
                        ):
                            self._render_resources(resources)

    def _render_resources(self, resources: list) -> None:
        """Create diagram nodes for a list of resources."""
        for resource in resources:
            node = create_node(resource)
            if node is not None:
                self.node_refs[resource.id] = node
