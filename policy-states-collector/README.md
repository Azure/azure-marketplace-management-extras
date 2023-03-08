# Policy states collector

The policy states collector application queries the state of the Azure Policies deployed with the Marketplace managed applications.
Then it sends their compliance states to the policy monitor table in the Log Analytics workspace (which is also deployed into the customers subscription by the marketplace offer). Additionaly, alert will be triggered if a policy is non-compliant.

## Authentication

The function source code is written in Python and relies on the [`DefaultAzureCredential()`](https://docs.microsoft.com/en-us/dotnet/api/azure.identity.defaultazurecredential?view=azure-dotnet)
class for authentication to Azure. Locally, it will use the AZ CLI credentials;

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

## Run tests

Unit tests are defined in the `PolicyStates/test_func.py` file. You can easily run them with pytest.

```bash
$ pip install pytest
...
$ pytest PolicyStates
================================================= test session starts ==================================================
platform linux -- Python 3.9.10, pytest-7.1.1, pluggy-1.0.0
rootdir: /home/user/projects/notification-endpoint
collected 10 items

PolicyStates/test_func.py ..........                                                                      [100%]

================================================== 10 passed in 0.15s ==================================================
```

## Useful links

- [Azure Functions Python developer guide](https://docs.microsoft.com/en-us/azure/azure-functions/functions-reference-python?tabs=asgi%2Cazurecli-linux%2Capplication-level)
- [Quickstart: Create a function in Azure with Python using Visual Studio Code](https://docs.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python)
