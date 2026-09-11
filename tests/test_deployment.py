"""Exercise the real botocore waiter model without network or AWS credentials."""
import unittest
import boto3
from botocore.exceptions import WaiterError
from botocore.stub import Stubber
from scripts.deploy_application import deploy_functions


class DeploymentWaiterTests(unittest.TestCase):
    def setUp(self):
        self.client = boto3.client("lambda", region_name="us-east-1", aws_access_key_id="unit-test", aws_secret_access_key="unit-test")
        self.stub = Stubber(self.client)
        self.name = "threatlens-test-api"
        self.archive = b"unit-test-package"

    def update_response(self):
        self.stub.add_response("update_function_code", {"FunctionName": self.name, "LastUpdateStatus": "InProgress"}, {"FunctionName": self.name, "ZipFile": self.archive})

    def poll(self, state):
        self.stub.add_response("get_function_configuration", {"FunctionName": self.name, "LastUpdateStatus": state}, {"FunctionName": self.name})

    def test_update_waits_using_only_configuration_permission(self):
        self.update_response(); self.poll("InProgress"); self.poll("Successful")
        with self.stub:
            deploy_functions(self.client, {"api": self.name}, self.archive, {"Delay": 0, "MaxAttempts": 3})
        self.stub.assert_no_pending_responses()

    def test_failed_update_stops_before_next_function(self):
        self.update_response(); self.poll("Failed")
        with self.stub, self.assertRaises(WaiterError):
            deploy_functions(self.client, {"api": self.name, "processor": "threatlens-test-processor"}, self.archive, {"Delay": 0, "MaxAttempts": 3})
        self.stub.assert_no_pending_responses()

    def test_in_progress_update_has_bounded_polling(self):
        self.update_response(); self.poll("InProgress"); self.poll("InProgress")
        with self.stub, self.assertRaises(WaiterError):
            deploy_functions(self.client, {"api": self.name}, self.archive, {"Delay": 0, "MaxAttempts": 2})
        self.stub.assert_no_pending_responses()


if __name__ == "__main__":
    unittest.main()
