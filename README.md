# Overview

This project features an Azure Function consisting of two applications designed to automatically track deployed Managed Applications. For further information about each function, please refer to the README file located in the `applications` directory.

These functions were created as part of the development process for the Managed Application offer and are highly reusable, making them an excellent starting point for others looking to build similar solutions.

## Repository content

Within this repository, you can find the following directories:

- `.github/workflows`: automated workflows to deploy infrastructure and code.
- `azure`: infrastructure templates that deploy the Azure components needed to support applications.
- `applications`: code and documentation describing each application in more details.

## Deployment

This project is a starting point to monitor your Managed Application offer created in [Partner center]<https://partner.microsoft.com/>. It is ?expectable? that you have already created your offer.

1. Set up your managed app Service Principal:

In the home page, navigate to market place offers > [your offer] > [your managed plane] > Plan overview > Technical configuration

In the Authorizations section, create a Service Principal with the owner role that will have access to Managed applications.   Note down the Service Principal information from the Partner Center portal.(Partner Center (microsoft.com)), we’ll use this in next step

1. Follow this [doc](https://learn.microsoft.com/en-us/cli/azure/create-an-azure-service-principal-azure-cli) to Create the Service Principal (SP) which will log in into Azure for creating infrastructure

1. Give Owner role to your created SP from previous step by using [this guidance](https://learn.microsoft.com/en-us/azure/role-based-access-control/role-assignments-cli)

1. Copy whole repo into your github project.

1. Add below secrets [your github repo] > Settings > Secrets and varibles > New repository secret
SP credentials from previous step `CLIENT_ID, CLIENT_SECRET, SUBSCRIPTION_ID` and `TENANT_ID`
SP from Managed application offer `SP_CLIENT_ID` and `SP_CLIENT_SECRET`

1. Add varibles in Varibles section > New repository varibles (next to Secrets section from previous step).

`APP_NAME` eg marketplace
`LOCATION` eg northeurope
`RESOURCE_GROUP_NAME` eg marketplace-manage-applications
`STORAGE_ACCOUNT_TABLE_NAME` eg marketplace-manage-applications
`SUBSCRIPTION_NAME` your subscription name where github SP was created

1. Everything is pre configured and ready to run `.github/workflows/infrastructure-deployment.yml`. Go to Actions > i
Infrastructure deployment > Run workflow
After the workflow is finished, copy function name from logs in `Show function name` step

1. Deploy code by running Code deployment workflow. Input function name that you copied from previous step.

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
