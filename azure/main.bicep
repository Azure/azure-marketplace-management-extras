targetScope = 'resourceGroup'

var logAnalyticsWorkspaceName = 'logAnalyticsMarketplace'
var policyStatesTableName = 'PolicyComplianceStates_CL'
var streamDeclaration = 'Custom-${policyStatesTableName}'
var storageAccountTableName = 'default'

param appName string
param location string = resourceGroup().location

@secure()
param spClientId string
@secure()
param spClientSecret string
@secure()
param spTenantId string

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

resource containerLogTable 'Microsoft.OperationalInsights/workspaces/tables@2022-10-01' = {
  parent: logAnalyticsWorkspace
  name: 'ContainerLog'
  properties: {
    plan: 'Analytics'
    retentionInDays: 7
    totalRetentionInDays: 7
    policyStatesTableName: policyStatesTableName
  }
}

resource policyContainerLogTable 'Microsoft.OperationalInsights/workspaces/tables@2021-12-01-preview' = {
  parent: logAnalyticsWorkspace
  name: policyStatesTableName
  properties: {
    plan: 'Analytics' // Needs to be Analytics plan to configure alerts on this data
    schema: {
      name: policyStatesTableName
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
          type: 'dateTime'
        }
      ]
    }
    retentionInDays: 7
    totalRetentionInDays: 7
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
      actionGroups: [
        actionGroupAlerts.id
      ]
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
    evaluationFrequency: 'PT5M'
    skipQueryValidation: true
    scopes: [
      logAnalyticsWorkspace.id
    ]
    severity: 1
    windowSize: 'PT5M'
  }
}

module policyStatesCollectorFunction 'function.bicep' = {
  name: 'marketplacefunction'
  params: {
    location: location
    logAnalyticsWorkspaceName: logAnalyticsWorkspace.name
    logAnalyticsWorkspaceId: logAnalyticsWorkspace.id
    streamDeclaration: streamDeclaration
    streamName: streamDeclaration
    spClientId: spClientId
    spClientSecret: spClientSecret
    spTenantId: spTenantId
    storageAccountTableName: storageAccountTableName
    appName: appName
  }
  dependsOn: [
    containerLogTable
  ]
}

output policyStatesCollectorFunctionName string = policyStatesCollectorFunction.outputs.functionAppName
