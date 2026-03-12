"""Tests for diagram node mapper."""

import os
import tempfile

from diagrams import Diagram

from cloud_mapper.diagram.node_mapper import create_node, get_node_class
from cloud_mapper.discovery.models import Resource, ResourceType


class TestNodeMapper:
    def test_get_node_class_ec2(self):
        cls = get_node_class(ResourceType.EC2_INSTANCE)
        assert cls is not None

    def test_get_node_class_s3(self):
        cls = get_node_class(ResourceType.S3_BUCKET)
        assert cls is not None

    def test_get_node_class_nlb(self):
        cls = get_node_class(ResourceType.LOAD_BALANCER, {"Type": "network"})
        assert cls is not None

    def test_get_node_class_alb_default(self):
        cls = get_node_class(ResourceType.LOAD_BALANCER, {"Type": "application"})
        assert cls is not None

    def test_get_node_class_nlb_differs_from_alb(self):
        nlb_cls = get_node_class(ResourceType.LOAD_BALANCER, {"Type": "network"})
        alb_cls = get_node_class(ResourceType.LOAD_BALANCER, {"Type": "application"})
        assert nlb_cls is not alb_cls

    def test_get_node_class_unknown(self):
        cls = get_node_class(ResourceType.ROUTE_TABLE)
        assert cls is None

    def test_create_node(self):
        resource = Resource(
            id="i-123",
            type=ResourceType.EC2_INSTANCE,
            name="web-server",
            region="us-east-1",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            with Diagram("test", show=False, filename=os.path.join(tmpdir, "test")):
                node = create_node(resource)
                assert node is not None

    def test_create_node_truncates_long_name(self):
        resource = Resource(
            id="i-123",
            type=ResourceType.EC2_INSTANCE,
            name="a" * 50,
            region="us-east-1",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            with Diagram("test", show=False, filename=os.path.join(tmpdir, "test")):
                node = create_node(resource)
                assert node is not None

    def test_create_node_unsupported_type(self):
        resource = Resource(
            id="rtb-123",
            type=ResourceType.ROUTE_TABLE,
            name="rt",
            region="us-east-1",
        )
        node = create_node(resource)
        assert node is None

    def test_all_main_types_have_mappings(self):
        """Ensure all important resource types have node classes."""
        important_types = [
            ResourceType.EC2_INSTANCE,
            ResourceType.LAMBDA_FUNCTION,
            ResourceType.S3_BUCKET,
            ResourceType.RDS_INSTANCE,
            ResourceType.LOAD_BALANCER,
            ResourceType.DYNAMODB_TABLE,
            ResourceType.SNS_TOPIC,
            ResourceType.SQS_QUEUE,
            ResourceType.API_GATEWAY,
            ResourceType.CLOUDFRONT_DISTRIBUTION,
            ResourceType.ROUTE53_ZONE,
        ]
        for rtype in important_types:
            assert get_node_class(rtype) is not None, f"Missing mapping for {rtype}"
