"""Tests for discovery coordinator."""

import boto3
import pytest
from moto import mock_aws

from cloud_mapper.discovery.coordinator import DiscoveryCoordinator
from cloud_mapper.discovery.models import ResourceType


@pytest.fixture
def coordinator_env():
    with mock_aws():
        session = boto3.Session(region_name="us-east-1")
        ec2 = session.client("ec2", region_name="us-east-1")
        yield session, ec2


class TestDiscoveryCoordinator:
    def test_discover_vpc_and_ec2(self, coordinator_env):
        session, ec2 = coordinator_env
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        vpc_id = vpc["Vpc"]["VpcId"]
        subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")
        subnet_id = subnet["Subnet"]["SubnetId"]
        ec2.run_instances(
            ImageId="ami-12345",
            MinCount=1,
            MaxCount=1,
            InstanceType="t3.micro",
            SubnetId=subnet_id,
        )

        coordinator = DiscoveryCoordinator(
            session, regions=["us-east-1"], services=["vpc", "ec2"]
        )
        graph = coordinator.discover_all()

        vpcs = graph.get_resources_by_type(ResourceType.VPC)
        subnets = graph.get_resources_by_type(ResourceType.SUBNET)
        instances = graph.get_resources_by_type(ResourceType.EC2_INSTANCE)

        assert len(vpcs) >= 1
        assert len(subnets) >= 1
        assert len(instances) >= 1

    def test_relationships_are_resolved(self, coordinator_env):
        session, ec2 = coordinator_env
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        vpc_id = vpc["Vpc"]["VpcId"]
        subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")
        subnet_id = subnet["Subnet"]["SubnetId"]
        result = ec2.run_instances(
            ImageId="ami-12345", MinCount=1, MaxCount=1, SubnetId=subnet_id
        )
        instance_id = result["Instances"][0]["InstanceId"]

        coordinator = DiscoveryCoordinator(
            session, regions=["us-east-1"], services=["vpc", "ec2"]
        )
        graph = coordinator.discover_all()

        children = graph.get_children(vpc_id)
        subnet_ids = [c.id for c in children]
        assert subnet_id in subnet_ids

        instance_children = graph.get_children(subnet_id)
        instance_ids = [c.id for c in instance_children]
        assert instance_id in instance_ids

    def test_discover_s3(self, coordinator_env):
        session, _ = coordinator_env
        s3 = session.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="my-test-bucket")

        coordinator = DiscoveryCoordinator(
            session, regions=["us-east-1"], services=["s3"]
        )
        graph = coordinator.discover_all()

        buckets = graph.get_resources_by_type(ResourceType.S3_BUCKET)
        assert len(buckets) == 1
        assert buckets[0].name == "my-test-bucket"

    def test_empty_services(self, coordinator_env):
        session, _ = coordinator_env
        coordinator = DiscoveryCoordinator(
            session, regions=["us-east-1"], services=["dynamodb"]
        )
        graph = coordinator.discover_all()
        assert len(graph.resources) == 0
