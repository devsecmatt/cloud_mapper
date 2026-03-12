# cloud_mapper

Discover all AWS resources in an account and generate an architecture diagram.

Scans 14 AWS services (VPC, EC2, ELB, RDS, S3, Lambda, ECS, DynamoDB, SNS, SQS, API Gateway, Route53, CloudFront, IAM) across all regions and produces a diagram with proper AWS icons, VPC/subnet grouping, and relationship edges.

## Setup

```bash
# System dependency (required by diagrams library)
brew install graphviz

# Install with uv
uv venv
uv pip install -e ".[dev]"
```

## Usage

```bash
# Scan a single region and generate a diagram
cloud-mapper --profile myprofile --region us-east-1 --output my-architecture

# Scan all regions
cloud-mapper --profile myprofile

# Save discovered resources to JSON for offline re-rendering
cloud-mapper --profile myprofile --save-data resources.json

# Re-render diagram from cached data (no AWS calls)
cloud-mapper --from-data resources.json --output my-architecture

# Filter to a specific VPC
cloud-mapper --profile myprofile --region us-east-1 --vpc vpc-abc123

# Only scan specific services
cloud-mapper --profile myprofile --services ec2,rds,elb

# Output as SVG instead of PNG
cloud-mapper --profile myprofile --format svg
```

## Options

```
--region TEXT           Comma-separated AWS regions or 'all' [default: all]
--services TEXT         Comma-separated services or 'all' [default: all]
--vpc TEXT              Filter to a specific VPC ID
--output TEXT           Output file path [default: aws-architecture]
--format [png|svg|pdf]  Output format [default: png]
--save-data PATH        Save discovered resources to JSON
--from-data PATH        Load resources from JSON (skip AWS scan)
--profile TEXT          AWS profile name from ~/.aws/credentials
--verbose               Enable verbose logging
```

## AWS Credentials

Credentials are resolved via the standard boto3 chain:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS credentials file (`~/.aws/credentials`)
3. IAM instance profile / role
4. `--profile` flag to select a named profile

## Running Tests

```bash
uv run pytest
```
