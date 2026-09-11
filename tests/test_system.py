import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
from backend.domain import normalize, detect, public_ingress
from backend.processor import process_batch
from backend.api import serve
from backend.repository import Repository, Conflict, NotFound
from backend.notifier import handle_records
from scripts.generate_events import events


class MemoryRepository:
    def __init__(self): self.items = {}
    def create(self, incident):
        if incident["id"] in self.items: return False
        self.items[incident["id"]] = {**incident, "timeline": []}
        return True
    def list(self, cursor=None): return {"items": list(self.items.values()), "nextCursor": None}
    def get(self, key):
        if key not in self.items: raise NotFound()
        return deepcopy(self.items[key])
    def change(self, key, version, status, note, actor):
        item = self.items[key]
        if item["version"] != version: raise Conflict()
        item.update(status=status, version=version + 1)
        item["timeline"].append({"text": note, "actor": actor})
        return deepcopy(item)


def api_event(route, incident_id=None, body=None):
    return {"routeKey": route, "requestContext": {"authorizer": {"jwt": {"claims": {"sub": "analyst-1", "token_use": "access"}}}}, "pathParameters": {"id": incident_id}, "body": json.dumps(body or {})}


class DetectionTests(unittest.TestCase):
    def test_twelve_signals_produce_ten_findings(self):
        self.assertEqual(10, sum(detect(normalize(e)) is not None for e in events()))
    def test_all_severities_and_five_rules(self):
        found = [detect(normalize(e)) for e in events()]
        self.assertEqual({"CRITICAL", "HIGH", "MEDIUM"}, {i["severity"] for i in found if i})
        self.assertEqual(5, len({i["category"] for i in found if i}))
    def test_repeat_identity_is_stable(self):
        e = next(events())
        self.assertEqual(detect(normalize(e))["id"], detect(normalize(deepcopy(e)))["id"])
    def test_benign_policy_is_not_administrator_alert(self):
        e = next(events())
        e["detail"]["requestParameters"]["policyArn"] = "arn:aws:iam::aws:policy/ReadOnlyAccess"
        self.assertIsNone(detect(normalize(e)))
    def test_failed_mutation_does_not_claim_success(self):
        e = next(events())
        e["detail"]["errorCode"] = "AccessDenied"
        self.assertIsNone(detect(normalize(e)))
    def test_public_https_is_not_remote_admin(self):
        self.assertFalse(public_ingress({"ipPermissions": [{"fromPort": 443, "toPort": 443, "ipRanges": [{"cidrIp": "0.0.0.0/0"}]}]}))
    def test_public_ipv6_ssh_is_detected(self):
        self.assertTrue(public_ingress({"ipPermissions": [{"fromPort": 22, "toPort": 22, "ipv6Ranges": [{"cidrIpv6": "::/0"}]}]}))
    def test_unknown_source_and_missing_id_rejected(self):
        e = next(events()); e["source"] = "untrusted.example"
        with self.assertRaises(ValueError): normalize(e)
        e = next(events()); del e["id"]; del e["detail"]["eventID"]
        with self.assertRaises(ValueError): normalize(e)
    def test_naive_timestamp_is_rejected(self):
        e = next(events()); e["time"] = "2026-01-15T12:00:00"
        with self.assertRaises(ValueError): normalize(e)
    def test_generator_is_bounded_and_repeatable(self):
        self.assertEqual(list(events(12, 42)), list(events(12, 42)))
        with self.assertRaises(ValueError): list(events(101))


class ProcessorTests(unittest.TestCase):
    def test_duplicate_delivery_does_not_create_second_incident(self):
        e = next(events()); repository = MemoryRepository()
        batch = {"Records": [{"messageId": "one", "body": json.dumps(e)}, {"messageId": "two", "body": json.dumps(e)}]}
        self.assertEqual({"batchItemFailures": []}, process_batch(batch, repository))
        self.assertEqual(1, len(repository.items))
    def test_partial_failures_leave_successful_message_acknowledged(self):
        batch = {"Records": [{"messageId": "good", "body": json.dumps(next(events()))}, {"messageId": "bad", "body": "not-json"}]}
        self.assertEqual([{ "itemIdentifier": "bad" }], process_batch(batch, MemoryRepository())["batchItemFailures"])
    def test_storage_failure_is_retried(self):
        repository = Mock(); repository.create.side_effect = RuntimeError("throttled")
        self.assertEqual([{"itemIdentifier": "one"}], process_batch({"Records": [{"messageId": "one", "body": json.dumps(next(events()))}]}, repository)["batchItemFailures"])


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryRepository(); self.incident = detect(normalize(next(events())))
        self.repo.create(self.incident); self.key = self.incident["id"]
    def test_missing_auth_rejected(self):
        self.assertEqual(401, serve({"routeKey": "GET /incidents"}, self.repo)["statusCode"])
    def test_id_token_rejected(self):
        e = api_event("GET /incidents"); e["requestContext"]["authorizer"]["jwt"]["claims"]["token_use"] = "id"
        self.assertEqual(401, serve(e, self.repo)["statusCode"])
    def test_resolution_requires_reason(self):
        self.assertEqual(400, serve(api_event("PATCH /incidents/{id}", self.key, {"version": 1, "status": "RESOLVED"}), self.repo)["statusCode"])
    def test_update_persists_actor_and_timeline(self):
        result = serve(api_event("PATCH /incidents/{id}", self.key, {"version": 1, "status": "RESOLVED", "note": "Authorized lab action verified"}), self.repo)
        self.assertEqual(200, result["statusCode"])
        self.assertEqual("analyst-1", json.loads(result["body"])["timeline"][0]["actor"])
    def test_stale_update_conflicts(self):
        event = api_event("PATCH /incidents/{id}", self.key, {"version": 1, "status": "INVESTIGATING", "note": "Checking"})
        self.assertEqual(200, serve(event, self.repo)["statusCode"])
        self.assertEqual(409, serve(event, self.repo)["statusCode"])
    def test_mass_assignment_rejected(self):
        result = serve(api_event("PATCH /incidents/{id}", self.key, {"version": 1, "status": "OPEN", "severity": "LOW"}), self.repo)
        self.assertEqual(400, result["statusCode"])
    def test_missing_incident_returns_404(self):
        self.assertEqual(404, serve(api_event("GET /incidents/{id}", "a" * 24), self.repo)["statusCode"])
    def test_boolean_is_not_a_version(self):
        self.assertEqual(400, serve(api_event("PATCH /incidents/{id}", self.key, {"version": True, "status": "OPEN"}), self.repo)["statusCode"])


class PersistenceTests(unittest.TestCase):
    def test_timeline_query_reads_all_dynamodb_pages(self):
        client = Mock(); repo = Repository(client=client, table="unit-table")
        marker = repo.encode({"PK": "INCIDENT#abc", "SK": "EVENT#1"})
        client.query.side_effect = [{"Items": [repo.encode({"PK": "INCIDENT#abc", "SK": "META", "entity": "INCIDENT", "id": "abc"})], "LastEvaluatedKey": marker}, {"Items": [repo.encode({"PK": "INCIDENT#abc", "SK": "EVENT#2", "entity": "TIMELINE", "text": "Page two"})]}]
        self.assertEqual("Page two", repo.get("abc")["timeline"][0]["text"])
        self.assertEqual(marker, client.query.call_args_list[1].kwargs["ExclusiveStartKey"])
    def test_create_atomically_writes_incident_timeline_outbox(self):
        client = Mock(); repo = Repository(client=client, table="unit-table")
        self.assertTrue(repo.create(detect(normalize(next(events())))))
        writes = client.transact_write_items.call_args.kwargs["TransactItems"]
        self.assertEqual(3, len(writes)); self.assertIn("ConditionExpression", writes[0]["Put"])
        self.assertEqual("OUTBOX", writes[2]["Put"]["Item"]["entity"]["S"])
    def test_transaction_failure_only_duplicate_if_incident_exists(self):
        class Cancelled(Exception): pass
        client = Mock(); client.exceptions = SimpleNamespace(TransactionCanceledException=Cancelled)
        client.transact_write_items.side_effect = Cancelled()
        repo = Repository(client=client, table="unit-table")
        client.get_item.return_value = {"Item": {"PK": {"S": "existing"}}}
        self.assertFalse(repo.create(detect(normalize(next(events())))))
        client.get_item.return_value = {}
        with self.assertRaises(Cancelled): repo.create(detect(normalize(next(events()))))
    def test_bad_cursor_rejected_before_database_query(self):
        client = Mock(); repo = Repository(client=client, table="unit-table")
        with self.assertRaises(ValueError): repo.list("not-a-cursor")
        client.query.assert_not_called()


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.event = {"Records": [{"eventName": "INSERT", "dynamodb": {"SequenceNumber": "123", "NewImage": {"entity": {"S": "OUTBOX"}, "PK": {"S": "OUTBOX#abc"}}}}]}
        self.table, self.sns = Mock(), Mock()
        self.item = {"status": "PENDING", "incidentId": "abc", "severity": "HIGH", "title": "Sample"}
        self.table.get_item.return_value = {"Item": self.item}
    def test_notifications_off_never_publishes(self):
        self.assertEqual([], handle_records(self.event, self.table, self.sns, "topic", False)["batchItemFailures"])
        self.sns.publish.assert_not_called()
        self.assertEqual("SIMULATED", self.table.update_item.call_args.kwargs["ExpressionAttributeValues"][":sent"])
    def test_publish_contains_deduplication_identity(self):
        handle_records(self.event, self.table, self.sns, "topic", True)
        self.assertEqual("abc", json.loads(self.sns.publish.call_args.kwargs["Message"])["idempotencyKey"])
    def test_already_sent_is_skipped(self):
        self.item["status"] = "SENT"
        handle_records(self.event, self.table, self.sns, "topic", True)
        self.sns.publish.assert_not_called()
    def test_publish_failure_is_returned_for_retry(self):
        self.sns.publish.side_effect = RuntimeError("unavailable")
        self.assertEqual([{"itemIdentifier": "123"}], handle_records(self.event, self.table, self.sns, "topic", True)["batchItemFailures"])
        self.table.update_item.assert_not_called()
    def test_publish_then_marker_failure_exposes_at_least_once_window(self):
        self.table.update_item.side_effect = RuntimeError("interrupted")
        self.assertEqual(1, len(handle_records(self.event, self.table, self.sns, "topic", True)["batchItemFailures"]))
        handle_records(self.event, self.table, self.sns, "topic", True)
        self.assertEqual(2, self.sns.publish.call_count)


if __name__ == "__main__": unittest.main()
