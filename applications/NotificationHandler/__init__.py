import logging
import re
import os

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ApplicationClient
from azure.data.tables import TableClient
from azure.core.exceptions import ResourceExistsError, HttpResponseError


def parse_resource_id(resource_id: str):

    pattern = "\/?subscriptions\/(?P<subscription_id>[0-9a-z-]+)\/resourceGroups\/(?P<resource_group>[a-zA-Z0-9-_.()]+)(|\/providers\/Microsoft\.Solutions\/applications\/(?P<application_name>[a-zA-Z0-9-_.()]+))$"
    m = re.match(pattern, resource_id)

    if not m:
        raise ValueError("Could not parse resource id")
    return (
        m.group("subscription_id"),
        m.group("resource_group"),
        m.group("application_name")
    )


def main(req: func.HttpRequest) -> func.HttpResponse:
    CONNECTION_STRING = str(os.environ["AzureWebJobsStorage"])
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

    # Obtain app subscription id and resource group from webhook call
    try:
        (
            app_subscription_id,
            app_resource_group,
            app_name
        ) = parse_resource_id(application_id)
    except ValueError as e:
        msg = f"Error obtaining app subscription and resource group: {e}"
        logging.error(msg)
        return func.HttpResponse(msg, status_code=500)

    logging.info(
        f"""
        event_type={event_type},
        provisioning_state={provisioning_state},
        app_subscription_id={app_subscription_id},
        app_resource_group={app_resource_group},
        app_name={app_name}
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

    if provisioning_state not in ("Succeeded", "Deleted"):
        msg = f"Provisioning state is '{provisioning_state}'. Ignoring event..."
        logging.info(msg)
        return func.HttpResponse(msg, status_code=200)

    with TableClient.from_connection_string(conn_str=CONNECTION_STRING, table_name=TABLE_NAME) as table_client:
        if provisioning_state == "Succeeded" and event_type == "PUT":
            # At this point you can obtain data from the Managed Application
            # instance, like the input parameters, deployment outputs, plan version, etc.
            # You can check all the Application object attributes here:
            # https://github.com/Azure/azure-sdk-for-python/blob/830ccf6ab129bdd6b7343cfae39e4e8e4b3bfd4d/sdk/resources/azure-mgmt-resource/azure/mgmt/resource/managedapplications/models/_models_py3.py#L191
            try:
                app_client = ApplicationClient(credential, app_subscription_id)
                app_details = app_client.applications.get_by_id(application_id)
            except Exception as e:
                msg = f"Failed to obtain managed application details: {e}"
                logging.error(msg)
                return func.HttpResponse(msg, status_code=500)

            logging.info(app_details)
            try:
                (_, mrg_name, _) = parse_resource_id(
                    app_details.managed_resource_group_id)
                logging.info(f"Managed resource group name: {mrg_name}")
            except ValueError as e:
                msg = f"Error obtaining the mrg name: {e}"
                logging.error(msg)
                return func.HttpResponse(msg, status_code=500)

            entity = {
                "subscription_id": app_subscription_id,
                "app_resource_group_name": app_resource_group,
                "app_name": app_name,
                "mrg_name": mrg_name,
                "PartitionKey":  app_subscription_id,
                "RowKey": app_name
            }
            try:
                table_client.create_table()
            except HttpResponseError:
                logging.info("Table has already exists")

            try:
                resp = table_client.create_entity(entity=entity)
                logging.info(f"Entity successfully added. {resp}")
            except ResourceExistsError:
                logging.error("Entity already exists")
            except Exception as e:
                msg = f"Error trying to add entity: {e}"
                logging.error(msg)
                return func.HttpResponse(msg, status_code=500)

        if provisioning_state == "Deleted" and event_type == "DELETE":
            try:
                table_client.delete_entity(
                    row_key=app_name, partition_key=app_subscription_id)
                logging.info("Entity successfully deleted.")
            except Exception as e:
                msg = f"Error trying to delete entity: {e}"
                logging.error(msg)
                return func.HttpResponse(msg, status_code=500)

    return func.HttpResponse("OK", status_code=200)
