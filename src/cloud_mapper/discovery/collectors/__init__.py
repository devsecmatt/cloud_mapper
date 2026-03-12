"""Collector registry - maps service names to collector classes."""

from cloud_mapper.discovery.collectors.apigateway import ApiGatewayCollector
from cloud_mapper.discovery.collectors.cloudfront import CloudFrontCollector
from cloud_mapper.discovery.collectors.dynamodb import DynamoDBCollector
from cloud_mapper.discovery.collectors.ec2 import EC2Collector
from cloud_mapper.discovery.collectors.ecs import ECSCollector
from cloud_mapper.discovery.collectors.elb import ELBCollector
from cloud_mapper.discovery.collectors.iam import IAMCollector
from cloud_mapper.discovery.collectors.lambda_ import LambdaCollector
from cloud_mapper.discovery.collectors.rds import RDSCollector
from cloud_mapper.discovery.collectors.route53 import Route53Collector
from cloud_mapper.discovery.collectors.s3 import S3Collector
from cloud_mapper.discovery.collectors.sns import SNSCollector
from cloud_mapper.discovery.collectors.sqs import SQSCollector
from cloud_mapper.discovery.collectors.vpc import VPCCollector

COLLECTOR_MAP = {
    "vpc": VPCCollector,
    "ec2": EC2Collector,
    "elb": ELBCollector,
    "rds": RDSCollector,
    "s3": S3Collector,
    "lambda": LambdaCollector,
    "ecs": ECSCollector,
    "dynamodb": DynamoDBCollector,
    "sns": SNSCollector,
    "sqs": SQSCollector,
    "apigateway": ApiGatewayCollector,
    "route53": Route53Collector,
    "cloudfront": CloudFrontCollector,
    "iam": IAMCollector,
}
