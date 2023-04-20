import logging
import re
import os

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ApplicationClient
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceExistsError



def parse_application_id(resource_id: str):
    pattern = r"\/?subscriptions\/(?P<subscription_id>[0-9a-z-]*)\/resourceGroups\/(?P<resource_group>[a-zA-Z0-9-_.()]*)"
    m = re.match(pattern, resource_id)
    if not m:
        raise ValueError("Could not parse application id")
    return (
        m.group("subscription_id"),
        m.group("resource_group")
    )


def main(req: func.HttpRequest) -> func.HttpResponse:
    CONNECTION_STRING = str(os.environ["AzureWebJobsStorage2"])
    TABLE_NAME = str(os.environ["TABLE_NAME"])

    logging.info("Received webhook call from marketplace deployment")

    # Azure will only send POST requests
    if req.method != "POST":
        return func.HttpResponse(status_code=405)

    try:
        # Acquire a credential object for the app identity. When running in the cloud,
        # DefaultAzureCredential uses the app's managed identity (MSI) or user-assigned service principal.
        # When run locally, DefaultAzureCredential relies on environment variables named
        # AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID.
        #
        # Make sure the identity used has been authorized in Partner Center to manage
        # the application. Check the following link for more information:
        # https://docs.microsoft.com/en-us/azure/marketplace/plan-azure-app-managed-app#choose-who-can-manage-the-application
        credential = DefaultAzureCredential()

    except Exception as e:
        msg = f"Could not authenticate: {e}"
        logging.error(msg)
        return func.HttpResponse(msg, status_code=500)

    try:
        req_body = req.get_json()
        logging.debug(f"Request body: {req_body}")
        application_id = req_body["applicationId"]
        event_type = req_body["eventType"]
        provisioning_state = req_body["provisioningState"]
    except (ValueError, KeyError, AttributeError) as e:
        msg = f"Could not parse request: {e}"
        logging.error(msg)
        return func.HttpResponse(msg, status_code=400)

    # Obtain client subscription id and resource group from webhook call
    try:
        (
            client_subscription_id,
            client_resource_group,
        ) = parse_application_id(application_id)
    except ValueError as e:
        msg = f"Error obtaining client subscription and resource group: {e}"
        logging.error(msg)
        return func.HttpResponse(msg, status_code=500)

    logging.info(
        f"""
        event_type={event_type},
        provisioning_state={provisioning_state},
        client_subscription_id={client_subscription_id},
        client_resource_group={client_resource_group}
        """
    )

    # Check out this docs to understand all the different combinations of event type and
    # provisioning state and what events originate them.
    # https://docs.microsoft.com/en-us/azure/azure-resource-manager/managed-applications/publish-notifications#event-triggers
    #
    # The Notification service expects a 200 OK response. Otherwise, it will consider
    # the request as failed and it will keep retrying it. Therefore, even if the provisioning
    # state is Failed, we need to return a 200 OK if the message has been processed in the function.
    # https://docs.microsoft.com/en-us/azure/azure-resource-manager/managed-applications/publish-notifications#notification-retries

    # If the provisioning state is Failed, it will contain an additional error property with
    # information about the error that originated the failure.
    if provisioning_state == "Failed":
        error = req_body.get("error")
        msg = f"Something failed during a {event_type} event. Error: {error}"
        logging.error(msg)
        return func.HttpResponse(msg, status_code=200)

    # Ignore the Accepted provisioning state
    if provisioning_state == "Accepted":
        msg = f"Provisioning state is '{provisioning_state}'. Ignoring..."
        logging.info(msg)
        return func.HttpResponse(msg, status_code=200)

    # If the provisioning state is Succeeded or Deleted, obtain the managed application details
    try:
        app_client = ApplicationClient(credential, client_subscription_id)
        app_details = app_client.applications.get_by_id(application_id)
    except Exception as e:
        msg = f"Failed to obtain managed application details: {e}"
        logging.error(msg)
        return func.HttpResponse(msg, status_code=500)

    # At this point you can obtain data from the Managed Application
    # instance, like the input parameters, deployment outputs, plan version, etc.
    # You can check all the Application object attributes here:
    # https://github.com/Azure/azure-sdk-for-python/blob/830ccf6ab129bdd6b7343cfae39e4e8e4b3bfd4d/sdk/resources/azure-mgmt-resource/azure/mgmt/resource/managedapplications/models/_models_py3.py#L191
    logging.info(app_details)

    if provisioning_state == "Succeeded" and event_type == "PUT":
        try:
            (
                app_subscription_id,
                app_resource_group
            ) = parse_application_id(app_details.managed_resource_group_id)
            logging.info(
                f"""
                event_type={event_type},
                app_subscription_id={app_subscription_id},
                app_resource_group={app_resource_group}
                """
            )
        except ValueError as e:
            msg = f"Error obtaining managed application subscription id and resource group: {e}"
            logging.error(msg)
            return func.HttpResponse(msg, status_code=500)

        entity = {
                "subscription_id": app_subscription_id,
                "resource_group_name": app_resource_group,
                "PartitionKey":  app_subscription_id,
                "RowKey": app_resource_group
            }

        with TableServiceClient.from_connection_string(CONNECTION_STRING) as table_service_client:
                table_client = table_service_client.create_table_if_not_exists(table_name=TABLE_NAME)
                logging.info("Table name: {}".format(table_client.table_name))
                try:
                    resp = table_client.create_entity(entity=entity)
                    logging.info(resp)
                except ResourceExistsError:
                    logging.error("Entity already exists")

    if provisioning_state == "Deleted" and event_type == "DELETE":
        try:
            (
                app_subscription_id,
                app_resource_group
            ) = parse_application_id(app_details.managed_resource_group_id)
            logging.info(
                f"""
                event_type={event_type},
                app_subscription_id={app_subscription_id},
                app_resource_group={app_resource_group}
                """
            )
        except ValueError as e:
            msg = f"Error obtaining managed application subscription id and resource group: {e}"
            logging.error(msg)
            return func.HttpResponse(msg, status_code=500)

        with TableServiceClient.from_connection_string(CONNECTION_STRING) as table_service_client:
            table_client.delete_entity(row_key=app_resource_group, partition_key=app_subscription_id)
            logging.info("Successfully deleted")

    return func.HttpResponse("OK", status_code=200)
