from azure.mgmt.policyinsights.aio import PolicyInsightsClient

from azure.mgmt.policyinsights.models import QueryOptions
from azure.identity.aio import DefaultAzureCredential
# from azure.identity import ClientSecretCredential
from azure.identity.aio import ClientSecretCredential
import azure.functions as func
import asyncio
import logging
import os
import json
from azure.monitor.ingestion import LogsIngestionClient
from azure.monitor.ingestion import UploadLogsStatus
from typing import List
# from azure.data.tables import TableClient
from azure.data.tables.aio import TableClient


async def get_resource_group_policies(policy_client, subscription_id, resource_group_name):
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


async def get_policies(policy_client, subscription_id, resource_group_name):
    try:
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

        if len(contoso_policies) == 0:
            logging.warning("There are not any contoso policies")
        else:
            return contoso_policies
    except Exception as e:
        msg = f"Failed to get policies for RG {resource_group_name}, error: {e}"
        logging.error(msg)


async def run():

    all_applications_policies_to_upload = []
    # async with TableClient.from_connection_string(CONNECTION_STRING, TABLE_NAME) as table_client:
    #     managed_applications = table_client.query_entities(
    #         "xTenant eq 'true'", select=['resource_group_name', 'subscription_id'])

    #     async for managed_app in managed_applications:
    #         logging.info("managed app resource group " +
    #                      managed_app["resource_group_name"] + "    " + managed_app["subscription_id"])
    #         result = get_policies(managed_app)
    #         logging.info(str(result))
    #         all_applications_policies_to_upload.append(result)

    async with ClientSecretCredential(
        AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET) as client_credential, PolicyInsightsClient(
            client_credential, subscription_id=sid) as policy_client:
        for application in applications:
            result = get_policies(
                policy_client, application["subscription_id"], application["resource_group_name"])
            all_applications_policies_to_upload.append(result)

        results = await asyncio.gather(*all_applications_policies_to_upload, return_exceptions=True)
        logging.info("results " + str(results))

    # # Upload policies
    # with DefaultAzureCredential() as default_credential:
    #     try:
    #         client = LogsIngestionClient(
    #             endpoint=DATA_COLLECTION_ENDPOINT, credential=default_credential, logging_enable=True)

    #         # https://learn.microsoft.com/en-us/azure/azure-monitor/logs/tutorial-logs-ingestion-portal#sample-data
    #         response = client.upload(
    #             rule_id=DATA_COLLECTION_IMMUTABLE_ID, stream_name=STREAM_NAME, logs=all_applications_policies_to_upload)
    #         if response.status != UploadLogsStatus.SUCCESS:
    #             failed_logs = response.failed_logs_index
    #             msg = f"Failed to send data to Log Analytics: {failed_logs}"
    #             logging.error(msg)
    #             return msg
    #     except Exception as e:
    #         msg = f"Failed to upload policies: {e}"
    #         logging.error(msg)
    #         return msg


def main(mytimer: func.TimerRequest) -> None:
    logging.info("Triggered by timer")
    asyncio.run(run())
    logging.info("Done")
