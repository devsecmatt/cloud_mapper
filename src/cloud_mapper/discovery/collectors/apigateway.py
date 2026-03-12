"""API Gateway resource collector - REST and HTTP APIs."""

from __future__ import annotations

import logging

import botocore.exceptions

from cloud_mapper.discovery.base import BaseCollector
from cloud_mapper.discovery.models import Resource, ResourceType

logger = logging.getLogger(__name__)


class ApiGatewayCollector(BaseCollector):
    service_name = "apigateway"

    def collect(self) -> list[Resource]:
        resources = []
        resources.extend(self._collect_rest_apis())
        resources.extend(self._collect_http_apis())
        return resources

    def _collect_rest_apis(self) -> list[Resource]:
        resources = []
        try:
            paginator = self.client.get_paginator("get_rest_apis")
            for page in paginator.paginate():
                for api in page["items"]:
                    resources.append(
                        Resource(
                            id=api["id"],
                            type=ResourceType.API_GATEWAY,
                            name=api.get("name", api["id"]),
                            region=self.region,
                            metadata={
                                "ApiType": "REST",
                                "Description": api.get("description"),
                            },
                        )
                    )
        except botocore.exceptions.ClientError as e:
            logger.debug("Could not list REST APIs: %s", e)
        return resources

    def _collect_http_apis(self) -> list[Resource]:
        resources = []
        try:
            apigwv2 = self.session.client("apigatewayv2", region_name=self.region)
            response = apigwv2.get_apis()
            for api in response.get("Items", []):
                resources.append(
                    Resource(
                        id=api["ApiId"],
                        type=ResourceType.API_GATEWAY,
                        name=api.get("Name", api["ApiId"]),
                        region=self.region,
                        metadata={
                            "ApiType": "HTTP",
                            "ProtocolType": api.get("ProtocolType"),
                            "Description": api.get("Description"),
                        },
                    )
                )
        except botocore.exceptions.ClientError as e:
            logger.debug("Could not list HTTP APIs: %s", e)
        return resources
