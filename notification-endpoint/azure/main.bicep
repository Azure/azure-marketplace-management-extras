targetScope = 'resourceGroup'

param appName string
param location string = resourceGroup().location
// Service principal credentials

@secure()
param spClientId string
@secure()
param spClientSecret string
@secure()
param spTenantId string

var uniqueName = '${appName}-${substring(replace(guid(resourceGroup().id), '-', ''), 0, 8)}'
// Storage account and Key Vault names must be between 3 and 24 characters in length and use numbers and lower-case letters only.
var uniqueNameWithoutDashes = toLower(replace(uniqueName, '-', ''))

var storageAccountName = length(uniqueNameWithoutDashes) > 24 ? substring(uniqueNameWithoutDashes, 0, 24) : uniqueNameWithoutDashes
var storageAccountConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${listKeys(storageAccount.id, storageAccount.apiVersion).keys[0].value}'
var hostingPlanName = uniqueName
var appInsightsName = uniqueName
var functionAppName = uniqueName
var keyvaultName = uniqueNameWithoutDashes
var logAnalyticsWorkspaceName = 'logAnalytics'

resource storageAccount 'Microsoft.Storage/storageAccounts@2022-09-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
  tags: {
    // circular dependency means we can't reference functionApp directly  /subscriptions/<subscriptionId>/resourceGroups/<rg-name>/providers/Microsoft.Web/sites/<appName>"
    'hidden-link:/subscriptions/${subscription().id}/resourceGroups/${resourceGroup().name}/providers/Microsoft.Web/sites/${functionAppName}': 'Resource'
  }
}

resource keyvault 'Microsoft.KeyVault/vaults@2021-10-01' = {
  name: keyvaultName
  location: location
  properties: {
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: true
    tenantId: subscription().tenantId
    accessPolicies: []
    sku: {
      name: 'standard'
      family: 'A'
    }
  }
}

resource secretClientId 'Microsoft.KeyVault/vaults/secrets@2021-10-01' = {
  name: '${keyvault.name}/spClientId'
  properties: {
    value: spClientId
  }
}
resource secretClientSecret 'Microsoft.KeyVault/vaults/secrets@2021-10-01' = {
  name: '${keyvault.name}/spClientSecret'
  properties: {
    value: spClientSecret
  }
}
resource secretTenantId 'Microsoft.KeyVault/vaults/secrets@2021-10-01' = {
  name: '${keyvault.name}/spTenantId'
  properties: {
    value: spTenantId
  }
}

resource accessPolicies 'Microsoft.KeyVault/vaults/accessPolicies@2021-10-01' = {
  name: '${keyvault.name}/add'
  properties: {
    accessPolicies: [
      {
        objectId: function.identity.principalId
        tenantId: function.identity.tenantId
        permissions: {
          secrets: [
            'get'
          ]
        }
      }
    ]
  }
}

resource hostingPlan 'Microsoft.Web/serverfarms@2021-03-01' = {
  name: hostingPlanName
  location: location
  kind: 'linux'
  properties: {
    // true if it's a Linux plan, false otherwise.
    reserved: true
  }
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
}

resource function 'Microsoft.Web/sites@2021-03-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: hostingPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.9'
      appSettings: [
        {
          name: 'AzureWebJobsDashboard'
          value: storageAccountConnectionString
        }
        {
          name: 'AzureWebJobsStorage'
          value: storageAccountConnectionString
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: storageAccountConnectionString
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'AZURE_CLIENT_ID'
          value: '@Microsoft.KeyVault(SecretUri=${secretClientId.properties.secretUriWithVersion})'
        }
        {
          name: 'AZURE_CLIENT_SECRET'
          value: '@Microsoft.KeyVault(SecretUri=${secretClientSecret.properties.secretUriWithVersion})'
        }
        {
          name: 'AZURE_TENANT_ID'
          value: '@Microsoft.KeyVault(SecretUri=${secretTenantId.properties.secretUriWithVersion})'
        }
      ]
    }
  }
}

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// action groups
resource actionGroupAlerts 'Microsoft.Insights/actionGroups@2022-06-01' = {
  name: 'actionGroup'
  location: 'global'
  properties: {
    enabled: true
    groupShortName: 'shortNsme'
    emailReceivers: [
      {
        emailAddress: 'your@email.com'
        name: 'myname'
        useCommonAlertSchema: false
      }
    ]
  }
}

// non compliance policy
resource nonCompliantPoliciesAlert 'Microsoft.Insights/scheduledQueryRules@2022-06-15' = {
  name: 'nonCompliantPoliciesAlert'
  location: location
  kind: 'LogAlert'
  properties: {
    actions: {
      actionGroups: actionGroupAlerts.id //
    }
    criteria: {
      allOf: [
        {
          operator: 'LessThanOrEqual'
          query: 'PolicyComplianceStates_CL | summarize arg_max(TimeGenerated,*) by Policy_assignment_id | where Is_compliant==false'
          threshold: 0
          timeAggregation: 'Count'
        }
      ]
    }
    displayName: 'Non-compliant policies'
    enabled: true
    evaluationFrequency: 'PT1M'
    scopes: [
      logAnalyticsWorkspace.id
    ]
    severity: 1
    windowSize: 'PT5M'
  }
}

output functionAppName string = function.name
