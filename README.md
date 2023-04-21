# Overview

This project features an Azure Function consisting of two applications designed to automatically track deployed Managed Applications. For further information about each function, please refer to the README file located in the `applications` directory.

These functions were created as part of the development process for the Managed Application offer and are highly reusable, making them an excellent starting point for others looking to build similar solutions.

## Repository content

Within this repository, you can find the following directories:

- `.github/workflows`: automated workflows to deploy infrastructure and code.
- `azure`: infrastructure templates that deploy the Azure components needed to support applications.
- `applications`: code and documentation describing each application in more details.

## Get it up and running

This project is a starting point to monitor your Managed Application offer created in [Partner center]<https://partner.microsoft.com/>. It is ?expectable? that you have already created your offer. Use guidance below:

### Prerequisites

The deployment of the azure function requires a series of actions to set up the environment, including the creation of a Marketplace [Managed Application service principal](https://learn.microsoft.com/en-gb/partner-center/marketplace/plan-azure-app-managed-app#choose-who-can-manage-the-application), an Azure service principal, the configure of necessary GitHub secrets/varibles and deploying the code.

### Create Azure Service Principal

Follow these steps to create a Service Principal with the ?"Owner" role? scoped to the target Platform subscription. This Service Principal will be used by a GitHub-owned runner to authenticate to Azure and deploy the Azure function infrastructure.

- Log in to the required Azure Active Directory Tenant using the Azure CLI on your local device or via [Azure Cloud Shell](https://shell.azure.com): <br>
`az login --tenant [Tenant ID]`
- Select the target Platform subscription, inserting the Subscription ID where indicated: <br> `az account set --subscription [Subscription ID]`
- Create the Service Principal, providing an identifying name where indicated: <br> `az ad sp create-for-rbac --name [SP Name] --query "{ client_id: appId, client_secret: password, tenant_id: tenant }"`
- Capture the values of **client_id**, **client_secret** and **tenant_id** for later use. It is recommended that you do not persist this information to disk or share the client secret for security reasons.
- Grant the Service Principal "Owner" role on the target Platform subscription: <br> `az role assignment create --assignee [SP Client ID] --role "Owner" --scope /subscriptions/[Subscription ID]`

#### Create secrets and varibles

For each of the secrets defined in the table below, follow these steps to add each secret and varibles the corresponding value.

- Navigate to **your github repo** > **Settings** > **Secrets and varibles** > **New repository secret**

- Add the secret name and value, taking care to use the exact secret name provided as this is explicitly referenced in the GitHub workflow.

| Secret Name              | Example Value                        | Description |
| ------------------------ | ------------------------------------ | ----------- |
| GH_PAT                   | ghp_*********************************** | GitHub Personal Access Token as described in [prerequisites](#github-personal-access-token) |
| PLATFORM_SUBSCRIPTION_ID | 3edb65d1-d7a8-409b-a320-3c01ac6825f9 | Subscription ID for core platform components including the Private Runner deployed as part of this workflow. |
| PLATFORM_SP_CLIENT_ID    | 9505fb9a-96e6-46d1-ac9b-2f74ee57f6d6 | Client ID from the [Service Principal creation](#create-service-principal) |
| PLATFORM_SP_CLIENT_SECRET | [secure string] | Client Secret from the [Service Principal creation](#create-service-principal) |
| TENANT    | f7d23806-d8ac-4576-814f-0ee931ffeab3 | Azure AD Tenant ID from the [Service Principal creation](#create-service-principal) |

SP credentials from previous step `CLIENT_ID, CLIENT_SECRET, SUBSCRIPTION_ID` and `TENANT_ID`
SP from Managed application offer `SP_CLIENT_ID` and `SP_CLIENT_SECRET`

- Navigate to **Settings** > **Secrets and varibles** > **Varibles** > **New repository varibles**

- Add the varible name and value, taking care to use the exact secret name provided as this is explicitly referenced in the GitHub workflow.

| Secret Name              | Example Value                        | Description |
| ------------------------ | ------------------------------------ | ----------- |
| GH_PAT                   | ghp_*********************************** | GitHub Personal Access Token as described in [prerequisites](#github-personal-access-token) |
| PLATFORM_SUBSCRIPTION_ID | 3edb65d1-d7a8-409b-a320-3c01ac6825f9 | Subscription ID for core platform components including the Private Runner deployed as part of this workflow. |
| PLATFORM_SP_CLIENT_ID    | 9505fb9a-96e6-46d1-ac9b-2f74ee57f6d6 | Client ID from the [Service Principal creation](#create-service-principal) |
| PLATFORM_SP_CLIENT_SECRET | [secure string] | Client Secret from the [Service Principal creation](#create-service-principal) |
| TENANT    | f7d23806-d8ac-4576-814f-0ee931ffeab3 | Azure AD Tenant ID from the [Service Principal creation](#create-service-principal) |

`APP_NAME` eg marketplace
`LOCATION` eg northeurope
`RESOURCE_GROUP_NAME` eg marketplace-manage-applications
`STORAGE_ACCOUNT_TABLE_NAME` eg marketplace-manage-applications
`SUBSCRIPTION_NAME` your subscription name where github SP was created

### Run the workflows

Follow these steps to run workflows which will deploy infrastructure and the code.

- Navigate to **Actions** -> **Infrastructure deployment**
- Click **Run workflow**
- Ensure the desired branch is selected, e.g. **main**
- Click the **Run workflow** button
- Copy function name from logs in `Show function name` step after the `Infrastructure deployment` workflow is finished
- Navigate to `Code deployment` workflow to run the second one. Paste the function name in input.

### Confirm Azure function applications are running successfully

Once all Workflows have completed, navigate to Resource group `marketplace-manage-applications`. Select Azure function and click on `Functions`. You should see `NotificationHandler` and `PolicyStates`. Each functions has logs that can indicate the status. You can find them in `Monitor` section.

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit <https://cla.opensource.microsoft.com>.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
