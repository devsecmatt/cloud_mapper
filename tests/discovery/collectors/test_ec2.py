"""Tests for EC2 collector."""

import boto3
import pytest
from moto import mock_aws

from cloud_mapper.discovery.collectors.ec2 import EC2Collector
from cloud_mapper.discovery.models import ResourceType


@pytest.fixture
def ec2_env():
    with mock_aws():
        session = boto3.Session(region_name="us-east-1")
        ec2 = session.client("ec2", region_name="us-east-1")
        yield session, ec2


class TestEC2Collector:
    def test_collect_instances(self, ec2_env):
        session, ec2 = ec2_env
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        vpc_id = vpc["Vpc"]["VpcId"]
        subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")
        subnet_id = subnet["Subnet"]["SubnetId"]

        instances = ec2.run_instances(
            ImageId="ami-12345",
            MinCount=1,
            MaxCount=1,
            InstanceType="t3.micro",
            SubnetId=subnet_id,
        )
        instance_id = instances["Instances"][0]["InstanceId"]
        ec2.create_tags(
            Resources=[instance_id], Tags=[{"Key": "Name", "Value": "test-instance"}]
        )

        collector = EC2Collector(session, "us-east-1")
        resources = collector.collect()

        ec2_instances = [r for r in resources if r.type == ResourceType.EC2_INSTANCE]
        test_instance = next((i for i in ec2_instances if i.id == instance_id), None)
        assert test_instance is not None
        assert test_instance.name == "test-instance"
        assert test_instance.metadata["InstanceType"] == "t3.micro"
        assert test_instance.metadata["VpcId"] == vpc_id
        assert test_instance.metadata["SubnetId"] == subnet_id

    def test_skips_terminated_instances(self, ec2_env):
        session, ec2 = ec2_env
        instances = ec2.run_instances(
            ImageId="ami-12345", MinCount=1, MaxCount=1, InstanceType="t3.micro"
        )
        instance_id = instances["Instances"][0]["InstanceId"]
        ec2.terminate_instances(InstanceIds=[instance_id])

        collector = EC2Collector(session, "us-east-1")
        resources = collector.collect()

        ec2_instances = [r for r in resources if r.type == ResourceType.EC2_INSTANCE]
        assert not any(i.id == instance_id for i in ec2_instances)

    def test_collect_security_groups(self, ec2_env):
        session, ec2 = ec2_env
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        vpc_id = vpc["Vpc"]["VpcId"]

        sg = ec2.create_security_group(
            GroupName="test-sg",
            Description="Test security group",
            VpcId=vpc_id,
        )
        sg_id = sg["GroupId"]

        collector = EC2Collector(session, "us-east-1")
        resources = collector.collect()

        sgs = [r for r in resources if r.type == ResourceType.SECURITY_GROUP]
        test_sg = next((s for s in sgs if s.id == sg_id), None)
        assert test_sg is not None
        assert test_sg.name == "test-sg"
        assert test_sg.metadata["VpcId"] == vpc_id
