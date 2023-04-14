import datetime
from azure.data.tables.aio import TableClient
from azure.identity.aio import ClientSecretCredential
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import unittest
from unittest.mock import patch
from . import run, main, get_policies
from unittest.mock import AsyncMock, patch
import pytest


class MockTimer():
    def __init__(self):
        self.past_due = True


class TestRun(unittest.TestCase):
    @patch('PolicyStates.TableClient.from_connection_string')
    @patch('PolicyStates.ClientSecretCredential')
    # @patch('asyncio.gather')
    def test_run(self, mock_client_secret_credential, mock_table_client):
        mock_client_secret_credential.return_value.__aiter__.return_value = AsyncMock(
            return_value=[1])
        mock_table_client.query_entities.return_value = [1,2]


        # Set up the mock result from the table query

        # mock_table_client.query_entities.return_value = MagicMock(
        #     return_value=[1])

        timer = MockTimer()
        resp = main(timer)
#         self.assertEqual(
#             resp,
#             "There are not any policies"
#         )
        # mock_client_secret_credential.assert_called_once_with(
        #     'AZURE_TENANT_ID22', 'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET')
        # mock_table_client.assert_called_once_with.from_connection_string(
        #     'CONNECTION_STRING', 'TABLE_NAME')

        # expected_query = "xTenant eq 'true'"
        # expected_select = ['resource_group_name', 'subscription_id']
        # mock_table_client.return_value.query_entities.assert_called_once_with(
        #     expected_query, select=expected_select)

        # mock_get_policies.assert_has_calls([AsyncMock(return_value=[{"Policy_assignment_name": "policy2"}, {"Policy_assignment_name": "policy2"}, 5]),
        #                                     AsyncMock(return_value=[{"Policy_assignment_name": "policy3"}, {"Policy_assignment_name": "policy4"}, 2])])

        # mock_gather.assert_called_once_with(
        #     [mock_get_policies.return_value, mock_get_policies.return_value], return_exceptions=True)

        # mock_run.assert_called_once()

    # async def test_get_policies(self):
    #     mock_client_credential = Mock()
    #     mock_subscription_id = "mock-subscription-id"
    #     mock_resource_group_name = "mock-resource-group-name"

    #     mock_policy_assignment_state1 = Mock(
    #         policy_assignment_name="policy-1",
    #         policy_assignment_id="id-1",
    #         is_compliant=True,
    #         timestamp=datetime(2022, 1, 1),
    #     )
    #     mock_policy_assignment_state2 = Mock(
    #         policy_assignment_name="policy-2",
    #         policy_assignment_id="id-2",
    #         is_compliant=False,
    #         timestamp=datetime(2022, 1, 2),
    #     )

    #     mock_policy_client = Mock()
    #     mock_policy_client.get_resource_group_policy_states = AsyncMock(return_value=[
    #         mock_policy_assignment_state1,
    #         mock_policy_assignment_state2,
    #     ])

    #     expected_policies = [
    #         {
    #             'Policy_assignment_name': 'policy-1',
    #             'Policy_assignment_id': 'id-1',
    #             'Is_compliant': True,
    #             'TimeGenerated': '"2022-01-01T00:00:00"'
    #         },
    #         {
    #             'Policy_assignment_name': 'policy-3',
    #             'Policy_assignment_id': 'id-2',
    #             'Is_compliant': False,
    #             'TimeGenerated': '"2022-01-02T00:00:00"'
    #         }
    #     ]

    #     result = await get_policies(mock_client_credential, mock_subscription_id, mock_resource_group_name)
    #     self.assertEqual(
    #         result,
    #         "There are not any policies"
    #     )
    #     mock_policy_client.get_resource_group_policy_states.assert_called_once_with(
    #         resource_group_name=mock_resource_group_name)
