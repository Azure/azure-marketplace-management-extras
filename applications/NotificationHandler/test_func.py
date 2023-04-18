import unittest
from unittest.mock import patch
import json

import azure.functions as func
from . import main


class TestFunction(unittest.TestCase):

    succeeded_event = {
        "eventType": "PUT",
        "applicationId": "subscriptions/bb5840c6-bd1f-4431-b82a-bcff37b7fd07/resourceGroups/managed-test/providers/Microsoft.Solutions/applications/test3",
        "eventTime": "2022-03-14T19:20:08.1707163Z",
        "provisioningState": "Succeeded",
        "plan": {
            "name": "msft-insights-poc-managed",
            "product": "msft-insights-poc-preview",
            "publisher": "test_test_agcicemarketplace1616064700629",
            "version": "0.1.20",
        },
    }

    failed_event = {
        "eventType": "PUT",
        "applicationId": "subscriptions/bb5840c6-bd1f-4431-b82a-bcff37b7fd07/resourceGroups/managed-test/providers/Microsoft.Solutions/applications/test3",
        "eventTime": "2022-03-14T19:20:08.1707163Z",
        "provisioningState": "Failed",
        "plan": {
            "name": "msft-insights-poc-managed",
            "product": "msft-insights-poc-preview",
            "publisher": "test_test_agcicemarketplace1616064700629",
            "version": "0.1.20",
        },
        "error": {
            "code": "ErrorCode",
            "message": "error message",
            "details": [{"code": "DetailedErrorCode", "message": "error message"}],
        },
    }

    @patch("NotificationHandler.DefaultAzureCredential")
    @patch("NotificationHandler.os")
    def test_ignore_get_method(self, os_env, mock_credential):
        req = func.HttpRequest(method="GET", url="/api/resource", body=None)
        resp = main(req)
        self.assertEqual(
            resp.status_code,
            405,
        )

    @patch("NotificationHandler.DefaultAzureCredential")
    @patch("NotificationHandler.os")
    def test_ignore_put_method(self, os_env, mock_credential):
        req = func.HttpRequest(method="PUT", url="/api/resource", body=None)
        resp = main(req)
        self.assertEqual(
            resp.status_code,
            405,
        )

    @patch("NotificationHandler.DefaultAzureCredential")
    @patch("NotificationHandler.os")
    def test_ignore_delete_method(self, os_env, mock_credential):
        req = func.HttpRequest(method="DELETE", url="/api/resource", body=None)
        resp = main(req)
        self.assertEqual(
            resp.status_code,
            405,
        )

    @patch("NotificationHandler.DefaultAzureCredential")
    @patch("NotificationHandler.os")
    def test_ignore_patch_method(self, os_env, mock_credential):
        req = func.HttpRequest(method="PATCH", url="/api/resource", body=None)
        resp = main(req)
        self.assertEqual(
            resp.status_code,
            405,
        )

    @patch("NotificationHandler.DefaultAzureCredential")
    @patch("NotificationHandler.os")
    def test_invalid_nonjson_payload(self, os_env, mock_credential):
        req = func.HttpRequest(method="post", url="/api/resource", body="foobar")
        resp = main(req)
        self.assertIn(
            b"Could not parse request",
            resp.get_body(),
        )
        self.assertEqual(
            resp.status_code,
            400,
        )

    @patch("NotificationHandler.DefaultAzureCredential")
    @patch("NotificationHandler.os")
    def test_failed_put_event(self, os_env, mock_credential):
        json_body = json.dumps(self.failed_event)
        req = func.HttpRequest(
            method="post",
            url="/api/resource",
            body=json_body.encode(),
        )
        resp = main(req)
        self.assertIn(
            b"Something failed during a PUT event",
            resp.get_body(),
        )
        self.assertIn(
            b"DetailedErrorCode",
            resp.get_body(),
        )
        self.assertEqual(
            resp.status_code,
            200,
        )

    @patch("NotificationHandler.DefaultAzureCredential")
    @patch("NotificationHandler.os")
    def test_failed_delete_event(self, os_env, mock_credential):
        body = self.failed_event.copy()
        body["eventType"] = "DELETE"
        json_body = json.dumps(body)
        req = func.HttpRequest(
            method="post",
            url="/api/resource",
            body=json_body.encode(),
        )
        resp = main(req)
        self.assertIn(
            b"Something failed during a DELETE event",
            resp.get_body(),
        )
        self.assertIn(
            b"DetailedErrorCode",
            resp.get_body(),
        )
        self.assertEqual(
            resp.status_code,
            200,
        )

    @patch("NotificationHandler.DefaultAzureCredential")
    @patch("NotificationHandler.os")
    def test_accepted_state(self, os_env, mock_credential):
        body = self.succeeded_event.copy()
        body["provisioningState"] = "Accepted"
        json_body = json.dumps(body)
        req = func.HttpRequest(
            method="post",
            url="/api/resource",
            body=json_body.encode(),
        )
        resp = main(req)
        self.assertIn(
            b"Provisioning state is 'Accepted'. Ignoring",
            resp.get_body(),
        )
        self.assertEqual(
            resp.status_code,
            200,
        )

    @patch("NotificationHandler.DefaultAzureCredential")
    @patch("NotificationHandler.os")
    def test_deleting_state(self, os_env, mock_credential):
        body = self.succeeded_event.copy()
        body["provisioningState"] = "Deleting"
        json_body = json.dumps(body)
        req = func.HttpRequest(
            method="post",
            url="/api/resource",
            body=json_body.encode(),
        )
        resp = main(req)
        self.assertIn(
            b"Provisioning state is 'Deleting'. Ignoring",
            resp.get_body(),
        )
        self.assertEqual(
            resp.status_code,
            200,
        )

    @patch("NotificationHandler.DefaultAzureCredential")
    @patch("NotificationHandler.ApplicationClient")
    @patch("NotificationHandler.os")
    @patch("NotificationHandler.TableServiceClient")
    def test_succeeded_state(self, table_client_mock, os_env, mock_client, mock_credential):
        json_body = json.dumps(self.succeeded_event)
        req = func.HttpRequest(
            method="post",
            url="/api/resource",
            body=json_body.encode(),
        )
        resp = main(req)
        self.assertEqual(
            b"OK",
            resp.get_body(),
        )
        self.assertEqual(
            resp.status_code,
            200,
        )
