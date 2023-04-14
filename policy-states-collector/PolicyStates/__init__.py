from __future__ import annotations
from azure.mgmt.policyinsights.aio import PolicyInsightsClient
from azure.mgmt.policyinsights.models import QueryOptions
from azure.identity.aio import ManagedIdentityCredential
from azure.identity.aio import ClientSecretCredential
import azure.functions as func
import asyncio
from collections import AsyncIterable

from azure.monitor.ingestion.aio import LogsIngestionClient
from azure.core.exceptions import HttpResponseError
from azure.data.tables.aio import TableClient

import logging
import os
import json
from typing import List

# DATA_COLLECTION_ENDPOINT = str(os.environ["DATA_COLLECTION_ENDPOINT"])
# DATA_COLLECTION_IMMUTABLE_ID = str(
#     os.environ["DATA_COLLECTION_IMMUTABLE_ID"])
# STREAM_NAME = str(os.environ["STREAM_NAME"])
# AZURE_TENANT_ID = str(os.environ["AZURE_TENANT_ID"])
# AZURE_CLIENT_ID = str(os.environ["AZURE_CLIENT_ID"])
# AZURE_CLIENT_SECRET = str(os.environ["AZURE_CLIENT_SECRET"])
# CONNECTION_STRING = str(os.environ["AzureWebJobsStorage"])
# TABLE_NAME = str(os.environ["TABLE_NAME"])

DATA_COLLECTION_ENDPOINT = "test"
DATA_COLLECTION_IMMUTABLE_ID = "test"
STREAM_NAME = "test"
AZURE_TENANT_ID = "test"
AZURE_CLIENT_ID = "test"
AZURE_CLIENT_SECRET = "test"
CONNECTION_STRING = "test"
TABLE_NAME = "test"


async def get_resource_group_policies(policy_client, subscription_id, resource_group_name) -> AsyncIterable:
    # Do not change or remove filter. It is used to query policies specifically assigned for RG
    scope = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}"
    filter = "PolicyAssignmentScope eq '{}'".format(scope)
    query_options = QueryOptions(filter=filter)

    # Only need latest evaluated policies
    return policy_client.policy_states.list_query_results_for_resource_group(
        policy_states_resource='latest',
        subscription_id=subscription_id,
        resource_group_name=resource_group_name,
        query_options=query_options)


async def get_policies(client_credential, subscription_id, resource_group_name) -> List[dict] | None:
    try:
        async with PolicyInsightsClient(
                client_credential, subscription_id=subscription_id) as policy_client:

            policy_assignment_states = await get_resource_group_policies(policy_client, subscription_id, resource_group_name)

            # Build up body object with only necessary values
            policies: List[dict] = []

            async for policy in policy_assignment_states:
                policies.append({
                    'Policy_assignment_name': policy.policy_assignment_name,
                    'Policy_assignment_id': policy.policy_assignment_id,
                    'Is_compliant': policy.is_compliant,
                    'TimeGenerated': json.dumps(policy.timestamp, default=str)
                })

            logging.info(
                f"Policies amount: {str(len(policies))} for RG {resource_group_name}")

            if len(policies) == 0:
                logging.warning("There are not any policies")
            else:
                return policies
    except Exception as e:
        msg = f"Failed to get/filter policies for RG {resource_group_name}, error: {e}"
        logging.error(msg)


async def run() -> None:
    all_applications_policies_to_upload = []
    async with ClientSecretCredential(
        AZURE_TENANT_ID,
        AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
    ) as client_credential, TableClient.from_connection_string(
        CONNECTION_STRING, TABLE_NAME
    ) as table_client:
        managed_applications = table_client.query_entities(
            "xTenant eq 'true'", select=['resource_group_name', 'subscription_id'])

        async for application in managed_applications:
            result = get_policies(
                client_credential, application["subscription_id"], application["resource_group_name"])
            all_applications_policies_to_upload.append(result)

        # policies_upload = await asyncio.gather(*all_applications_policies_to_upload, return_exceptions=True)

    # # Upload policies
    # async with ManagedIdentityCredential() as ingestion_credential, LogsIngestionClient(
    #         endpoint=DATA_COLLECTION_ENDPOINT, credential=ingestion_credential, logging_enable=True) as logs_client:
    #     try:
    #         await logs_client.upload(
    #             rule_id=DATA_COLLECTION_IMMUTABLE_ID, stream_name=STREAM_NAME, logs=policies_upload)
    #         logging.info(f'Uploaded {len(policies_upload)} policies')

    #     except HttpResponseError as e:
    #         logging.error(f"Upload failed: {e}")


def main(mytimer: func.TimerRequest) -> None:
    asyncio.run(run())
