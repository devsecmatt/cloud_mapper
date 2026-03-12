"""Tests for VPC collector."""

import boto3
import pytest
from moto import mock_aws

from cloud_mapper.discovery.collectors.vpc import VPCCollector
from cloud_mapper.discovery.models import ResourceType


@pytest.fixture
def vpc_env():
    with mock_aws():
        session = boto3.Session(region_name="us-east-1")
        ec2 = session.client("ec2", region_name="us-east-1")
        yield session, ec2


class TestVPCCollector:
    def test_collect_vpcs(self, vpc_env):
        session, ec2 = vpc_env
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        vpc_id = vpc["Vpc"]["VpcId"]
        ec2.create_tags(
            Resources=[vpc_id], Tags=[{"Key": "Name", "Value": "test-vpc"}]
        )

        collector = VPCCollector(session, "us-east-1")
        resources = collector.collect()

        vpcs = [r for r in resources if r.type == ResourceType.VPC]
        test_vpc = next((v for v in vpcs if v.id == vpc_id), None)
        assert test_vpc is not None
        assert test_vpc.name == "test-vpc"
        assert test_vpc.metadata["CidrBlock"] == "10.0.0.0/16"

    def test_collect_subnets(self, vpc_env):
        session, ec2 = vpc_env
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        vpc_id = vpc["Vpc"]["VpcId"]

        subnet = ec2.create_subnet(
            VpcId=vpc_id, CidrBlock="10.0.1.0/24", AvailabilityZone="us-east-1a"
        )
        subnet_id = subnet["Subnet"]["SubnetId"]

        collector = VPCCollector(session, "us-east-1")
        resources = collector.collect()

        subnets = [r for r in resources if r.type == ResourceType.SUBNET]
        test_subnet = next((s for s in subnets if s.id == subnet_id), None)
        assert test_subnet is not None
        assert test_subnet.metadata["VpcId"] == vpc_id
        assert test_subnet.metadata["CidrBlock"] == "10.0.1.0/24"

    def test_collect_internet_gateways(self, vpc_env):
        session, ec2 = vpc_env
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        vpc_id = vpc["Vpc"]["VpcId"]

        igw = ec2.create_internet_gateway()
        igw_id = igw["InternetGateway"]["InternetGatewayId"]
        ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)

        collector = VPCCollector(session, "us-east-1")
        resources = collector.collect()

        igws = [r for r in resources if r.type == ResourceType.INTERNET_GATEWAY]
        test_igw = next((i for i in igws if i.id == igw_id), None)
        assert test_igw is not None
        assert vpc_id in test_igw.metadata["VpcIds"]

    def test_collect_nat_gateways(self, vpc_env):
        session, ec2 = vpc_env
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        vpc_id = vpc["Vpc"]["VpcId"]
        subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")
        subnet_id = subnet["Subnet"]["SubnetId"]

        eip = ec2.allocate_address(Domain="vpc")
        nat = ec2.create_nat_gateway(
            SubnetId=subnet_id, AllocationId=eip["AllocationId"]
        )
        nat_id = nat["NatGateway"]["NatGatewayId"]

        collector = VPCCollector(session, "us-east-1")
        resources = collector.collect()

        nats = [r for r in resources if r.type == ResourceType.NAT_GATEWAY]
        test_nat = next((n for n in nats if n.id == nat_id), None)
        assert test_nat is not None
        assert test_nat.metadata["SubnetId"] == subnet_id
        assert test_nat.metadata["VpcId"] == vpc_id
