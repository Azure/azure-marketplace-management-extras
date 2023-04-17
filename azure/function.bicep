param location string
param logAnalyticsWorkspaceName string
param logAnalyticsWorkspaceId string
param streamDeclaration string
param streamName string
param storageAccountTableName string
targetScope = 'resourceGroup'
param appName string

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

// allows to publish policy states to LA
var monitoringMetricsPublisherRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '3913510d-42f4-4e42-8a64-420c390055eb')
// allows reading reading resources
var readerRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'acdd72a7-3385-48ef-bd42-f606fba81ae7')
// allows to read subsciption id and rg name from Blob storage
var storageBlobReaderRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1')

resource storageAccount 'Microsoft.Storage/storageAccounts@2022-09-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
}

// update later to have correct fields
resource storageAccountTable 'Microsoft.Storage/storageAccounts/tableServices@2022-09-01' = {
  name: storageAccountTableName
  parent: storageAccount
  properties: {
    cors: {
      corsRules: []
    }
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
  parent: keyvault
  name: 'spClientId'
  properties: {
    value: spClientId
  }
}

resource secretClientSecret 'Microsoft.KeyVault/vaults/secrets@2021-10-01' = {
  parent: keyvault
  name: 'spClientSecret'
  properties: {
    value: spClientSecret
  }
}

resource secretTenantId 'Microsoft.KeyVault/vaults/secrets@2021-10-01' = {
  parent: keyvault
  name: 'spTenantId'
  properties: {
    value: spTenantId
  }
}

resource accessPolicies 'Microsoft.KeyVault/vaults/accessPolicies@2021-10-01' = {
  parent: keyvault
  name: 'add'
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

resource policyStatesDataCollectionEndpoint 'Microsoft.Insights/dataCollectionEndpoints@2021-09-01-preview' = {
  name: 'policyStatesDataCollectionEndpoint'
  location: location
  properties: {}
}

resource policyStatesDataCollectionRule 'Microsoft.Insights/dataCollectionRules@2021-09-01-preview' = {
  name: 'policyStatesDataCollectionRule'
  location: location
  properties: {
    dataCollectionEndpointId: policyStatesDataCollectionEndpoint.id
    streamDeclarations: {
      '${streamDeclaration}': {
        columns: [
          {
            name: 'Policy_assignment_id'
            type: 'string'
          }
          {
            name: 'Policy_assignment_name'
            type: 'string'
          }
          {
            name: 'Is_compliant'
            type: 'boolean'
          }
          {
            name: 'TimeGenerated'
            type: 'datetime'
          }
        ]
      }
    }
    dataSources: {}
    destinations: {
      logAnalytics: [
        {
          workspaceResourceId: logAnalyticsWorkspaceId
          name: logAnalyticsWorkspaceName
        }
      ]
    }
    dataFlows: [
      {
        streams: [
          streamDeclaration
        ]
        destinations: [
          logAnalyticsWorkspaceName
        ]
        transformKql: 'source'
        outputStream: streamDeclaration
      }
    ]
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
        {
          name: 'DATA_COLLECTION_ENDPOINT'
          value: policyStatesDataCollectionEndpoint.properties.logsIngestion.endpoint
        }
        {
          name: 'DATA_COLLECTION_IMMUTABLE_ID'
          value: policyStatesDataCollectionRule.properties.immutableId
        }
        {
          name: 'STREAM_NAME'
          value: streamName
        }
        {
          name: 'TABLE_NAME'
          value: storageAccountTableName
        }
      ]
    }
  }
}

resource policyIdentityReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid('policyIdentityReader', resourceGroup().id)
  properties: {
    principalId: function.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: readerRole
  }
}

resource monitoringMetricsPublisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid('monitoringMetricsPublisher', resourceGroup().id)
  properties: {
    principalId: function.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: monitoringMetricsPublisherRole
  }
}

resource storageBlobReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccount
  name: guid('storageBlobReader', resourceGroup().id)
  properties: {
    principalId: function.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobReaderRole
  }
}
