from azure.mgmt.policyinsights._policy_insights_client import PolicyInsightsClient
from azure.mgmt.policyinsights.models import QueryOptions
from azure.identity import DefaultAzureCredential
import azure.functions as func
import logging
import os
import json
from azure.monitor.ingestion import LogsIngestionClient, UploadLogsStatus

def get_policies(credential, SUBSCRIPTION_ID, RESOURCE_GROUP_NAME):
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

# Manualy trigger an endpoint
# https://docs.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer?tabs=in-process&pivots=programming-language-javascript


def main(mytimer: func.TimerRequest) -> None:
    # Environments need to be initialised inside main for mock testing
    SUBSCRIPTION_ID = str(os.environ["SUBSCRIPTION_ID"])
    RESOURCE_GROUP_NAME = str(os.environ["RESOURCE_GROUP_NAME"])
    DATA_COLLECTION_ENDPOINT = str(os.environ["DATA_COLLECTION_ENDPOINT"])
    DATA_COLLECTION_IMMUTABLE_ID = str(
        os.environ["DATA_COLLECTION_IMMUTABLE_ID"])
    STREAM_NAME = str(os.environ["STREAM_NAME"])

    logging.info("Triggered by timer")

    try:
        # Acquire a credential object for the app identity. When running in the cloud,
        # DefaultAzureCredential will use system's identity that has been created as part function deployment
        # Check the following link for more information:
        # https://docs.microsoft.com/en-us/azure/marketplace/plan-azure-app-managed-app#choose-who-can-manage-the-application
        credential = DefaultAzureCredential()
    except Exception as e:
        msg = f"Could not authenticate: {e}"
        logging.error(msg)
        return msg

    policies_response = get_policies(
        credential, SUBSCRIPTION_ID, RESOURCE_GROUP_NAME)

    # Build up body object with only necessary values
    policies = []
    policy_assignment_states = list(policies_response)
    try:
        if policy_assignment_states:
            for policy in policy_assignment_states:
                if policy.policy_assignment_name.startswith('myprefix-'):
                    policies.append({
                        'Policy_assignment_name': policy.policy_assignment_name,
                        'Policy_assignment_id': policy.policy_assignment_id,
                        'Is_compliant': policy.is_compliant,
                        'TimeGenerated': json.dumps(policy.timestamp, default=str)
                    })
        else:
            msg = "There are not any policies"
            logging.error(msg)
            return msg

    except Exception as e:
        msg = f"Failed to filter policy assignment states: {e}"
        logging.error(msg)
        return msg

    logging.info("policies length: " + str(len(policies)))

    if len(policies) == 0:
        logging.info("There are not any policies")
        return "There are not any policies"

    client = LogsIngestionClient(
        endpoint=DATA_COLLECTION_ENDPOINT, credential=credential, logging_enable=True)

    # https://learn.microsoft.com/en-us/azure/azure-monitor/logs/tutorial-logs-ingestion-portal#sample-data
    response = client.upload(
        rule_id=DATA_COLLECTION_IMMUTABLE_ID, stream_name=STREAM_NAME, logs=policies)
    if response.status != UploadLogsStatus.SUCCESS:
        failed_logs = response.failed_logs_index
        msg = f"Failed to send data to Log Analytics: {failed_logs}"
        logging.error(msg)
        return msg

    logging.info("Done")