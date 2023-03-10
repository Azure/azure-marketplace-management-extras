var logAnalyticsWorkspaceName = 'logAnalyticsMarketplace'
var policyStatesTableName = 'PolicyComplianceStates_CL'
var streamDeclaration = 'Custom-${policyStatesTableName}'

param location string = resourceGroup().location
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
  name: '${logAnalyticsWorkspaceName}/ContainerLog'
  properties: {
    plan: 'Analytics' // Consider 'Basic' plan for lower costs, see: https://samcogan.com/finally-cheaper-options-for-azure-monitor-logs/
    retentionInDays: 7
    totalRetentionInDays: 7
    policyStatesTableName: policyStatesTableName
  }
  dependsOn: [
    logAnalyticsWorkspace
  ]
}

// 2022-10-01 version is throwing error "Unsupported api version"
// Need to be tested again later
resource policyContainerLogTable 'Microsoft.OperationalInsights/workspaces/tables@2021-12-01-preview' = {
  name: '${logAnalyticsWorkspaceName}/${policyStatesTableName}'
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
  }
  dependsOn: [
    containerLogTable
  ]
}

// todo:
// create SP to push into LA and get data from Blob storage
// it will need reader role and publisher metrics roles

// output functionAppName string = function.name
