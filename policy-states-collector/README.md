# Policy states collector

The functionality that allows publishers to access and manage deployed customers managed application is the foundation upon which the entire solution is built.

The time-triggered Azure Function application, policy states collector, uses Azure APIs to query the latest state of Azure policies in managed applications. To build the correct request, the application retrieves the Resource Group name and subscription ID from Azure Blob Storage. The application leverages the Service Principal, which is configured in the Managed App plan, to access managed resource policies.

After retrieving the data, the application filters and sends it to the Policy Monitor table in the Log Analytics Workspace for real-time monitoring and analysis. It filters only the policies deployed by the Managed Application to ensure that no customers policies are pulled.

Finally, the Scheduled Query Rule Alert is configured to monitor non-compliant policies and triggers an Action Group for notification when an issue is detected.

This solution offers automated monitoring of Azure policies for compliance, allowing for proactive identification and resolution of policy violations.  

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

To get started, navigate to the `policy-monitor-trigger` directory and create your virtual environment.

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

## Useful links

- [Azure Functions Python developer guide](https://docs.microsoft.com/en-us/azure/azure-functions/functions-reference-python?tabs=asgi%2Cazurecli-linux%2Capplication-level)
- [Quickstart: Create a function in Azure with Python using Visual Studio Code](https://docs.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python)
