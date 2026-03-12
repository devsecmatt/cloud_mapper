"""Tests for S3 collector."""

import boto3
import pytest
from moto import mock_aws

from cloud_mapper.discovery.collectors.s3 import S3Collector
from cloud_mapper.discovery.models import ResourceType


@pytest.fixture
def s3_env():
    with mock_aws():
        session = boto3.Session(region_name="us-east-1")
        s3 = session.client("s3", region_name="us-east-1")
        yield session, s3


class TestS3Collector:
    def test_collect_buckets(self, s3_env):
        session, s3 = s3_env
        s3.create_bucket(Bucket="test-bucket-1")
        s3.create_bucket(
            Bucket="test-bucket-2",
            CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
        )

        collector = S3Collector(session, "us-east-1")
        resources = collector.collect()

        assert len(resources) == 2
        assert all(r.type == ResourceType.S3_BUCKET for r in resources)

        bucket_names = {r.name for r in resources}
        assert "test-bucket-1" in bucket_names
        assert "test-bucket-2" in bucket_names

        bucket_2 = next(r for r in resources if r.name == "test-bucket-2")
        assert bucket_2.region == "eu-west-1"

    def test_empty_account(self, s3_env):
        session, _ = s3_env
        collector = S3Collector(session, "us-east-1")
        resources = collector.collect()
        assert len(resources) == 0
