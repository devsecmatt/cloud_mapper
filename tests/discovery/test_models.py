"""Tests for data models."""

import json
import tempfile
from pathlib import Path

from cloud_mapper.discovery.models import Resource, ResourceGraph, ResourceType


class TestResource:
    def test_to_dict_roundtrip(self):
        resource = Resource(
            id="vpc-123",
            type=ResourceType.VPC,
            name="my-vpc",
            region="us-east-1",
            metadata={"CidrBlock": "10.0.0.0/16"},
        )
        data = resource.to_dict()
        restored = Resource.from_dict(data)

        assert restored.id == resource.id
        assert restored.type == resource.type
        assert restored.name == resource.name
        assert restored.region == resource.region
        assert restored.metadata == resource.metadata

    def test_to_dict_structure(self):
        resource = Resource(
            id="i-abc",
            type=ResourceType.EC2_INSTANCE,
            name="web",
            region="eu-west-1",
        )
        data = resource.to_dict()
        assert data == {
            "id": "i-abc",
            "type": "ec2_instance",
            "name": "web",
            "region": "eu-west-1",
            "metadata": {},
        }


class TestResourceGraph:
    def test_add_and_get_resources(self, sample_graph):
        vpcs = sample_graph.get_resources_by_type(ResourceType.VPC)
        assert len(vpcs) == 1
        assert vpcs[0].id == "vpc-123"

    def test_get_children(self, sample_graph):
        children = sample_graph.get_children("vpc-123")
        assert len(children) == 1
        assert children[0].id == "subnet-456"

    def test_get_children_nested(self, sample_graph):
        children = sample_graph.get_children("subnet-456")
        assert len(children) == 1
        assert children[0].id == "i-789"

    def test_filter_by_vpc(self, sample_graph):
        filtered = sample_graph.filter_by_vpc("vpc-123")
        assert "vpc-123" in filtered.resources
        assert "subnet-456" in filtered.resources
        assert "i-789" in filtered.resources
        # S3 and Lambda without VpcId should not be included
        assert "my-bucket" not in filtered.resources

    def test_merge(self):
        g1 = ResourceGraph()
        g1.add_resource(
            Resource(id="a", type=ResourceType.VPC, name="a", region="us-east-1")
        )
        g2 = ResourceGraph()
        g2.add_resource(
            Resource(id="b", type=ResourceType.S3_BUCKET, name="b", region="us-east-1")
        )
        g2.add_relationship("a", "b", "routes_to")

        g1.merge(g2)
        assert "a" in g1.resources
        assert "b" in g1.resources
        assert len(g1.relationships) == 1

    def test_json_roundtrip(self, sample_graph):
        data = sample_graph.to_dict()
        json_str = json.dumps(data)
        restored = ResourceGraph.from_dict(json.loads(json_str))

        assert len(restored.resources) == len(sample_graph.resources)
        assert len(restored.relationships) == len(sample_graph.relationships)

        for rid in sample_graph.resources:
            assert rid in restored.resources
            assert restored.resources[rid].name == sample_graph.resources[rid].name

    def test_json_file_roundtrip(self, sample_graph):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            sample_graph.to_json_file(path)
            restored = ResourceGraph.from_json_file(path)

            assert len(restored.resources) == len(sample_graph.resources)
            assert len(restored.relationships) == len(sample_graph.relationships)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_get_related(self, sample_graph):
        related = sample_graph.get_related("subnet-456")
        assert len(related) == 2  # vpc-123 (parent) and i-789 (child)
        related_ids = {r.id for r, _ in related}
        assert "vpc-123" in related_ids
        assert "i-789" in related_ids

    def test_empty_graph(self):
        graph = ResourceGraph()
        assert len(graph.resources) == 0
        assert len(graph.relationships) == 0
        assert graph.get_resources_by_type(ResourceType.VPC) == []
        assert graph.get_children("nonexistent") == []
