# Policy states collector

The functionality that allows publishers to access and manage deployed customers managed application is the foundation upon which the entire solution is built.

The time-triggered Azure Function application, policy states collector, uses Azure APIs to query the latest state of Azure policies in managed applications. To build the correct request, the application retrieves the Resource Group name and subscription ID from Azure Blob Storage. The application leverages the Service Principal, which is configured in the Managed App plan, to access managed resource policies.

After retrieving the data, the application filters and sends it to the Policy Monitor table in the Log Analytics Workspace for real-time monitoring and analysis. It filters only the policies deployed by the Managed Application to ensure that no customers policies are pulled.

Finally, the Scheduled Query Rule Alert is configured to monitor non-compliant policies and triggers an Action Group for notification when an issue is detected.

This solution offers automated monitoring of Azure policies for compliance, allowing for proactive identification and resolution of policy violations.

![diagram](https://github.com/Azure/marketplace-management/blob/main/applications/diagram.png)

## Solution components

- Azure Log Analytics
- Data collection rule and Data collection endpoint
- Azure function
- SP principles
- Azure storage table
- Azure Key vault
- Scheduled Query Rule Alert
- Action Group

## Authentication

The function source code is written in Python and relies on the [`ClientSecretCredential()`](https://learn.microsoft.com/en-us/dotnet/api/azure.identity.clientsecretcredential?view=azure-dotnet) and [`ManagedIdentityCredential()`](https://learn.microsoft.com/en-us/dotnet/api/azure.identity.managedidentitycredential?view=azure-dotnet)
classes for authentication to Azure.

Azure function has system assigned identity and two roles that allow read policies and write data to Log Analytics.

## Local setup

The function has the following requirements:

- AZ cli
- [Azure Functions runtime](https://docs.microsoft.com/en-us/azure/azure-functions/functions-versions?tabs=in-process%2Cv4&pivots=programming-language-python) version 4.x
- Python 3.9 and pip
- Virtualenv
- Also check out [Quickstart: Create a function in Azure with Python using Visual Studio Code](https://docs.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python#configure-your-environment)
to find out additional requirements and the recommended VS Code extensions.

To get started, navigate to the `applications` directory and create your virtual environment.

```sh
virtualenv .venv
```

Then you can source it and install the function dependencies in the `requirements.txt`.

```sh
source .venv/bin/activate
pip install -r requirements.txt
```

Update `function.json` to `"schedule": "* * * * * *"` for triggering application every second for testing purpose.

Set up all local envs. Take an existing deployed Azure Function name and then run `func azure functionapp fetch-app-settings <yourAFname>`
This will create `local.settings.json` file with all envs.

Last step is assign correct role for DataCollectionRule. Go to `Monitor > Data Collection Rules` and find your DCR. In `Acess Contorole` add role `Monitoring Metrics Publisher` to your account.

Run the function with `func start` command provided by the Azure Functions runtime.

# Notification Endpoint

This directory contains the necessary artifacts to deploy the Notification Endpoint that captures events triggered when the managed version of application is installed by customers from the Marketplace. To understand more about the process please check the [Managed Application deployment notifications](../docs/deploy-infrastructure.md) document.

The idea behind this project is to be used as a starter application that can be further customized to fit the needs of the publisher.
The Notification Endpoint is built as an [Azure Function](https://azure.microsoft.com/en-us/services/functions/) invoked via an HTTP trigger whose URL is configured as the notification endpoint URL of  the Managed Application.

> :warning: **Please make sure you deploy the Notification Endpoint before you publish your managed app offer. Otherwise, you will need to republish the offer again with configuration of the Notification Endpoint URL.**


## Requirements

1. According to the [Azure managed applications with notifications](https://docs.microsoft.com/en-us/azure/azure-resource-manager/managed-applications/publish-notifications#getting-started) docs, the endpoint should expect POST requests and should return `200 OK` if the request was processed successfully.

2. According to the [Provide a notification endpoint URL](https://docs.microsoft.com/en-us/azure/marketplace/azure-app-managed#provide-a-notification-endpoint-url) docs, Azure appends `/resource` to the notification endpoint URL before sending the request. Therefore, our function's invoke URL should end with `/resource`.

3. The function needs to parse the incoming request, which will contain a JSON-encoded payload with the schema defined in the [Azure Marketplace application notification schema](https://docs.microsoft.com/en-us/azure/azure-resource-manager/managed-applications/publish-notifications#azure-marketplace-application-notification-schema) docs.

4. It will also need to handle different types of [Event triggers](https://docs.microsoft.com/en-us/azure/azure-resource-manager/managed-applications/publish-notifications#event-triggers) which include a combination of event types (e.g. PUT, PATCH, DELETE) and provisioning states (e.g. Accepted, Succeeded, Failed).

5. If the provisioning state is "Succeeded", the function app will obtain the application ID from the payload and send an API call to obtain additional information about the deployment. This information includes data such as the name given by the customer, the input parameters or the output values of the deployment.
It will also save the managed app "subscription id" and "resource group name" into Azure storage table if event type is "PUT". This information will be used for "PolicyStates" function app.

5. If the provisioning state is "Deleted" and event type is "DELETE", the function app will delete the entity about manage app.

## Function configuration

To address requirements 1 and 2, we can use the `function.json` file to configure the HTTP methods our function will accept and the URL route to the function.

```json
{
...
      "methods": [
        "post"
      ],
      "route": "resource"
...
}
```

Check the [`NotificationHandler/function.json`](./NotificationHandler/function.json) file.

## Authentication

The function source code is written in Python and relies on the [`DefaultAzureCredential()`](https://docs.microsoft.com/en-us/dotnet/api/azure.identity.defaultazurecredential?view=azure-dotnet) class for authentication to Azure. Locally, it will use the AZ CLI credentials; and remotely, it will use the `AZURE_` environment variables that will be configured with the credentials of a Service Principal with authorization on the managed application.

## Local setup

The function has the following requirements:

- AZ cli
- [Azure Functions runtime](https://docs.microsoft.com/en-us/azure/azure-functions/functions-versions?tabs=in-process%2Cv4&pivots=programming-language-python) version 4.x
- Python 3.9 and pip
- Virtualenv
- Also check out [Quickstart: Create a function in Azure with Python using Visual Studio Code](https://docs.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python#configure-your-environment) to find out additional requirements and the recommended VS Code extensions.

To get started, navigate to the `notification-endpoint` directory and create your virtual environment.

```
virtualenv .venv
```

Then you can source it and install the function dependencies in the `requirements.txt`.

```
source .venv/bin/activate
pip install -r requirements.txt
```

Now, make sure you are logged in with your AZ cli tool, and run the function with the `func start` command provided by the Azure Functions runtime.

```
$ func start
Found Python version 3.9.10 (python3).

Azure Functions Core Tools
Core Tools Version:       4.0.3971 Commit hash: d0775d487c93ebd49e9c1166d5c3c01f3c76eaaf  (64-bit)
Function Runtime Version: 4.0.1.16815


Functions:

        NotificationHandler: [POST] http://localhost:7071/api/resource

For detailed output, run func with --verbose flag.
info: Microsoft.AspNetCore.Hosting.Diagnostics[1]
      Request starting HTTP/2 POST http://127.0.0.1:33909/AzureFunctionsRpcMessages.FunctionRpc/EventStream application/grpc -
info: Microsoft.AspNetCore.Routing.EndpointMiddleware[0]
      Executing endpoint 'gRPC - /AzureFunctionsRpcMessages.FunctionRpc/EventStream'
[2022-03-18T08:04:50.328Z] Worker process started and initialized.
[2022-03-18T08:04:54.925Z] Host lock lease acquired by instance ID '0000000000000000000000008B849374'.
```

Once running, open a new window or tab and you can use the `test_event_ok.json` and `test_event_failure.json` files in the `NotificationHandler` directory to send a sample requests to the function. From this directory, you can use curl to send an HTTP request. You can modify the sample file with an application ID that you have access to in order to test the entire flow.

```
curl -i -H "Content-Type: application/json" -X POST http://localhost:7071/api/resource -d @NotificationHandler/test_event_ok.json
```

You can also run the function from VS Code (tasks and launch configuration is provided in the `.vscode` directory). This will allow you to put breakpoints and easily debug and develop the function code.

If you want to test the App Registration (Service Principal) credentials, create a `local.settings.json` file with the environment variables that will be injected into the function when run locally. This will make the function use the provided environment variables for authentication instead of using the AZ cli credentials.

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_TENANT_ID": "<SP_TENANT_ID>",
    "AZURE_CLIENT_ID": "<SP_CLIENT_ID>",
    "AZURE_CLIENT_SECRET": "<SP_CLIENT_SECRET>"
  }
}
```

## Deployment to Azure

The [`azure`](./azure) directory contains the Bicep templates that deploy the infrastructure components of the Notification Endpoint. Additionally, a GitHub workflow has been created at [`../.github/workflows/notification-endpoint.yml`](../.github/workflows/notification-endpoint.yml) to automate the infrastructure deployment and the function app deployment.

Assuming you are logged in with the AZ cli tool, and you are targeting the appropriate subscription, you can manually trigger a deployment with following command.

```
az deployment group create -g <RESOURCE_GROUP> \
  --template-file azure/main.bicep \
  --parameters appName=notifications
```

Check the [Run the function in Azure](https://docs.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python#run-the-function-in-azure) docs to learn how to use VS Code to submit the function to Azure.

## Run tests

Unit tests are defined in the `NotificationHandler/test_func.py` file. You can easily run them with pytest.

```bash
$ pip install pytest
...
$ pytest NotificationHandler
================================================= test session starts ==================================================
platform linux -- Python 3.9.10, pytest-7.1.1, pluggy-1.0.0
rootdir: /home/user/projects/notification-endpoint
collected 10 items

NotificationHandler/test_func.py ..........                                                                      [100%]

================================================== 10 passed in 0.15s ==================================================
```

## Useful links

- [Azure Functions Python developer guide](https://docs.microsoft.com/en-us/azure/azure-functions/functions-reference-python?tabs=asgi%2Cazurecli-linux%2Capplication-level)
- [Quickstart: Create a function in Azure with Python using Visual Studio Code](https://docs.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python)
