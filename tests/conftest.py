"""Shared test fixtures."""

import boto3
import pytest
from moto import mock_aws

from cloud_mapper.discovery.models import Resource, ResourceGraph, ResourceType


@pytest.fixture
def aws_session():
    """Create a mocked boto3 session."""
    with mock_aws():
        session = boto3.Session(region_name="us-east-1")
        yield session


@pytest.fixture
def sample_graph():
    """Create a sample ResourceGraph for testing."""
    graph = ResourceGraph()

    # VPC
    graph.add_resource(
        Resource(
            id="vpc-123",
            type=ResourceType.VPC,
            name="test-vpc",
            region="us-east-1",
            metadata={"CidrBlock": "10.0.0.0/16"},
        )
    )

    # Subnet
    graph.add_resource(
        Resource(
            id="subnet-456",
            type=ResourceType.SUBNET,
            name="test-subnet",
            region="us-east-1",
            metadata={
                "VpcId": "vpc-123",
                "CidrBlock": "10.0.1.0/24",
                "AvailabilityZone": "us-east-1a",
                "MapPublicIpOnLaunch": True,
            },
        )
    )

    # EC2 Instance
    graph.add_resource(
        Resource(
            id="i-789",
            type=ResourceType.EC2_INSTANCE,
            name="web-server",
            region="us-east-1",
            metadata={
                "VpcId": "vpc-123",
                "SubnetId": "subnet-456",
                "InstanceType": "t3.micro",
                "State": "running",
            },
        )
    )

    # S3 Bucket
    graph.add_resource(
        Resource(
            id="my-bucket",
            type=ResourceType.S3_BUCKET,
            name="my-bucket",
            region="us-east-1",
        )
    )

    # Lambda
    graph.add_resource(
        Resource(
            id="arn:aws:lambda:us-east-1:123456789:function:my-func",
            type=ResourceType.LAMBDA_FUNCTION,
            name="my-func",
            region="us-east-1",
            metadata={"Runtime": "python3.12"},
        )
    )

    # Relationships
    graph.add_relationship("vpc-123", "subnet-456", "contains")
    graph.add_relationship("subnet-456", "i-789", "contains")

    return graph
