"""Tests for diagram renderer."""

import os
import tempfile

import pytest

from cloud_mapper.diagram.renderer import DiagramRenderer
from cloud_mapper.discovery.models import Resource, ResourceGraph, ResourceType


class TestDiagramRenderer:
    def test_render_produces_file(self, sample_graph):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test-diagram")
            renderer = DiagramRenderer(sample_graph, output_path, "png")
            result = renderer.render()

            assert os.path.exists(result)
            assert result.endswith(".png")
            assert os.path.getsize(result) > 0

    def test_render_empty_graph(self):
        graph = ResourceGraph()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "empty-diagram")
            renderer = DiagramRenderer(graph, output_path, "png")
            result = renderer.render()
            assert os.path.exists(result)

    def test_render_with_relationships(self):
        graph = ResourceGraph()

        # ALB -> EC2 instances
        graph.add_resource(
            Resource(
                id="vpc-1",
                type=ResourceType.VPC,
                name="prod-vpc",
                region="us-east-1",
                metadata={"CidrBlock": "10.0.0.0/16"},
            )
        )
        graph.add_resource(
            Resource(
                id="subnet-1",
                type=ResourceType.SUBNET,
                name="public-subnet",
                region="us-east-1",
                metadata={
                    "VpcId": "vpc-1",
                    "CidrBlock": "10.0.1.0/24",
                    "AvailabilityZone": "us-east-1a",
                    "MapPublicIpOnLaunch": True,
                },
            )
        )
        graph.add_resource(
            Resource(
                id="alb-1",
                type=ResourceType.LOAD_BALANCER,
                name="app-lb",
                region="us-east-1",
                metadata={"VpcId": "vpc-1", "Type": "application"},
            )
        )
        graph.add_resource(
            Resource(
                id="i-1",
                type=ResourceType.EC2_INSTANCE,
                name="app-server",
                region="us-east-1",
                metadata={"VpcId": "vpc-1", "SubnetId": "subnet-1"},
            )
        )

        graph.add_relationship("vpc-1", "subnet-1", "contains")
        graph.add_relationship("vpc-1", "alb-1", "contains")
        graph.add_relationship("subnet-1", "i-1", "contains")
        graph.add_relationship("alb-1", "i-1", "routes_to")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "rel-diagram")
            renderer = DiagramRenderer(graph, output_path, "png")
            result = renderer.render()

            assert os.path.exists(result)
            assert os.path.getsize(result) > 0
