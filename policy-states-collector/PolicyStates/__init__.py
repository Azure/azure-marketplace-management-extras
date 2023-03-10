from azure.mgmt.policyinsights._policy_insights_client import PolicyInsightsClient
from azure.mgmt.policyinsights.models import QueryOptions
from azure.identity import DefaultAzureCredential
from azure.identity import ClientSecretCredential
import azure.functions as func
import logging
import os
import json
from azure.monitor.ingestion import LogsIngestionClient
from azure.monitor.ingestion import UploadLogsStatus
from typing import List
from azure.data.tables import TableClient

DATA_COLLECTION_ENDPOINT = str(os.environ["DATA_COLLECTION_ENDPOINT"])
DATA_COLLECTION_IMMUTABLE_ID = str(
    os.environ["DATA_COLLECTION_IMMUTABLE_ID"])
STREAM_NAME = str(os.environ["STREAM_NAME"])
AZURE_TENANT_ID =
AZURE_CLIENT_ID =
AZURE_CLIENT_SECRET =
CONNECTION_STRING =
TABLE_NAME =


def get_resource_group_policies(credential, SUBSCRIPTION_ID, RESOURCE_GROUP_NAME):
    policyClient = PolicyInsightsClient(
        credential, subscription_id=SUBSCRIPTION_ID)
    # Do not change or remove filter. It is used to query policies specifically assigned for RG
    scope = f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP_NAME}"
    filter = "PolicyAssignmentScope eq '{}'".format(scope)
    query_options = QueryOptions(filter=filter)

    # Only need latest evaluated policies
    return policyClient.policy_states.list_query_results_for_resource_group(
        policy_states_resource='latest',
        subscription_id=SUBSCRIPTION_ID,
        resource_group_name=RESOURCE_GROUP_NAME,
        query_options=query_options)


def get_policies(client_credential, managed_app):
    policies_response = get_resource_group_policies(
        client_credential, managed_app["subscription_id"], managed_app["resource_group_name"])

    # Build up body object with only necessary values
    contoso_policies: List[dict] = []
    try:
        policy_assignment_states = list(policies_response)
    except Exception as e:
        msg = f"Failed to get policies: {e}"
        logging.error(msg)
        return

    if policy_assignment_states:
        for policy in policy_assignment_states:
            # if policy.policy_assignment_name.startswith('myprefix-'):
            contoso_policies.append({
                'Policy_assignment_name': policy.policy_assignment_name,
                'Policy_assignment_id': policy.policy_assignment_id,
                'Is_compliant': policy.is_compliant,
                'TimeGenerated': json.dumps(policy.timestamp, default=str)
            })

    logging.info("contoso policies length: " + str(len(contoso_policies)))

    if len(contoso_policies) == 0:
        logging.warning("There are not any contoso policies")
    else:
        return contoso_policies


def get_subscriptions():
    with TableClient.from_connection_string(CONNECTION_STRING, TABLE_NAME) as table_client:
        try:
            return list(table_client.query_entities(
                "xTenant eq 'true'", select=['resource_group_name', 'subscription_id']))
        except Exception as e:
            msg = f"Failed to get applications: {e}"
            logging.error(msg)
            return


def main(mytimer: func.TimerRequest) -> None:
    logging.info("Triggered by timer")

    try:
        # Acquire a credential object for the app identity. When running in the cloud,
        # DefaultAzureCredential will use system's identity that has been created as part function deployment
        # When run locally, DefaultAzureCredential relies on environment variables named
        # AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID.
        # Check the following link for more information:
        # https://docs.microsoft.com/en-us/azure/marketplace/plan-azure-app-managed-app#choose-who-can-manage-the-application
        # credential = DefaultAzureCredential()
        client_credential = ClientSecretCredential(
            AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)
    except Exception as e:
        msg = f"Could not authenticate: {e}"
        logging.error(msg)
        return msg

    managed_applications = get_subscriptions()
    all_applications_policies_to_upload = []

    for managed_app in managed_applications:
        logging.info("managed app resource group " +
                     managed_app["resource_group_name"])
        all_applications_policies_to_upload.append(
            get_policies(client_credential, managed_app))

    logging.info(str(all_applications_policies_to_upload))

    # Upload policies
    with DefaultAzureCredential() as default_credential:
        try:
            client = LogsIngestionClient(
                endpoint=DATA_COLLECTION_ENDPOINT, credential=default_credential, logging_enable=True)

            # https://learn.microsoft.com/en-us/azure/azure-monitor/logs/tutorial-logs-ingestion-portal#sample-data
            response = client.upload(
                rule_id=DATA_COLLECTION_IMMUTABLE_ID, stream_name=STREAM_NAME, logs=all_applications_policies_to_upload)
            if response.status != UploadLogsStatus.SUCCESS:
                failed_logs = response.failed_logs_index
                msg = f"Failed to send data to Log Analytics: {failed_logs}"
                logging.error(msg)
                return msg
        except Exception as e:
            msg = f"Failed to upload policies: {e}"
            logging.error(msg)
            return msg

    logging.info("Done")
