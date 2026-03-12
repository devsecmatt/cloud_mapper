"""Configuration constants and defaults."""

# Services that operate globally (not per-region)
GLOBAL_SERVICES = {"s3", "iam", "route53", "cloudfront"}

# Default region used for global service API calls
GLOBAL_REGION = "us-east-1"

# All supported services
ALL_SERVICES = [
    "vpc",
    "ec2",
    "elb",
    "rds",
    "s3",
    "lambda",
    "ecs",
    "dynamodb",
    "sns",
    "sqs",
    "apigateway",
    "route53",
    "cloudfront",
    "iam",
]

# Max workers for multi-region scanning
DEFAULT_MAX_WORKERS = 5

# Retry settings for throttled API calls
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0
