from __future__ import annotations
from azure.mgmt.policyinsights.aio import PolicyInsightsClient
from azure.mgmt.policyinsights.models import QueryOptions
from azure.identity.aio import DefaultAzureCredential
from azure.identity.aio import ClientSecretCredential
import azure.functions as func
import asyncio
from collections import AsyncIterable

from azure.monitor.ingestion.aio import LogsIngestionClient
from azure.monitor.ingestion import UploadLogsStatus
from azure.data.tables.aio import TableClient

import logging
import os
import json
import time
from typing import List

DATA_COLLECTION_ENDPOINT = str(os.environ["DATA_COLLECTION_ENDPOINT"])
DATA_COLLECTION_IMMUTABLE_ID = str(
    os.environ["DATA_COLLECTION_IMMUTABLE_ID"])
STREAM_NAME = str(os.environ["STREAM_NAME"])
AZURE_TENANT_ID = str(os.environ["AZURE_TENANT_ID"])
AZURE_CLIENT_ID = str(os.environ["AZURE_CLIENT_ID"])
AZURE_CLIENT_SECRET = str(os.environ["AZURE_CLIENT_SECRET"])
CONNECTION_STRING = str(os.environ["CONNECTION_STRING"])
TABLE_NAME = str(os.environ["TABLE_NAME"])


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
            contoso_policies: List[dict] = []

            async for policy in policy_assignment_states:
                # if policy.policy_assignment_name.startswith('myprefix-'):
                contoso_policies.append({
                    'Policy_assignment_name': policy.policy_assignment_name,
                    'Policy_assignment_id': policy.policy_assignment_id,
                    'Is_compliant': policy.is_compliant,
                    'TimeGenerated': json.dumps(policy.timestamp, default=str)
                })

            logging.info(
                f"Contoso policies amount: {str(len(contoso_policies))} for RG {resource_group_name}")

            if len(contoso_policies) == 0:
                logging.warning("There are not any contoso policies")
            else:
                return contoso_policies
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

        results = await asyncio.gather(*all_applications_policies_to_upload, return_exceptions=True)
        logging.info("results " + str(results))

    # Upload policies
    async with DefaultAzureCredential() as default_credential, LogsIngestionClient(
            endpoint=DATA_COLLECTION_ENDPOINT, credential=default_credential, logging_enable=True) as logs_client:
        response = await logs_client.upload(
            rule_id=DATA_COLLECTION_IMMUTABLE_ID, stream_name=STREAM_NAME, logs=[1])
        if response.status != UploadLogsStatus.SUCCESS:
            failed_logs = response.failed_logs_index
            msg = f"Failed to send data to Log Analytics: {failed_logs}"
            logging.error(msg)
            return msg
        else:
            logging.info("-------------COMPLETED------------")


def main(mytimer: func.TimerRequest) -> None:
    logging.info("-------------TRIGGERED BY TIMER-------------")
    tic = time.perf_counter()
    asyncio.run(run())
    toc = time.perf_counter()
    logging.info(
        f'took {toc - tic:0.4f} seconds'
    )
