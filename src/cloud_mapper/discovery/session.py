"""AWS session management and credential validation."""

from __future__ import annotations

import logging

import boto3
import botocore.exceptions

logger = logging.getLogger(__name__)


def create_session(profile: str | None = None) -> boto3.Session:
    """Create a boto3 session and validate credentials."""
    session = boto3.Session(profile_name=profile)

    # Validate credentials by calling STS
    try:
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        logger.info(
            "Authenticated as %s (Account: %s)",
            identity["Arn"],
            identity["Account"],
        )
    except botocore.exceptions.NoCredentialsError:
        raise SystemExit(
            "No AWS credentials found. Configure via 'aws configure', "
            "environment variables, or --profile."
        )
    except botocore.exceptions.ClientError as e:
        raise SystemExit(f"Failed to authenticate with AWS: {e}")

    return session


def get_enabled_regions(session: boto3.Session) -> list[str]:
    """Get all regions enabled for this account."""
    ec2 = session.client("ec2")
    response = ec2.describe_regions(
        Filters=[{"Name": "opt-in-status", "Values": ["opt-in-not-required", "opted-in"]}]
    )
    regions = [r["RegionName"] for r in response["Regions"]]
    regions.sort()
    return regions
