"""Bounded real-AWS smoke test. Publishes 12 safe demo events plus 3 replays.

Never sends SNS/email, invokes dangerous AWS APIs, or changes Cognito users.
Account, table and queue ownership are checked before publishing.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.domain import normalize, detect
from scripts.generate_events import events


def output_value(outputs, key):
    value = outputs[key]
    return value["value"] if isinstance(value, dict) and "value" in value else value


def require_project_resource(value):
    if not isinstance(value, str) or not value.startswith("threatlens-"):
        raise ValueError("Expected a ThreatLens project resource")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs", type=Path, required=True, help="Private terraform output -json file")
    parser.add_argument("--expected-account", required=True)
    parser.add_argument("--profile", default="portfolio")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--report", type=Path, default=ROOT / "docs" / "live-smoke-result.json")
    args = parser.parse_args()
    import boto3
    from boto3.dynamodb.types import TypeDeserializer
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    identity = session.client("sts").get_caller_identity()
    if identity["Account"] != args.expected_account or identity["Arn"].endswith(":root"):
        raise RuntimeError("Wrong account or root identity: refusing to publish")
    outputs = json.loads(args.outputs.read_text(encoding="utf-8-sig"))
    table_name = require_project_resource(output_value(outputs, "incident_table"))
    bus_name = require_project_resource(output_value(outputs, "event_bus_name"))
    queue_url = output_value(outputs, "queue_url")
    dlq_url = output_value(outputs, "dlq_url")
    for value in (queue_url, dlq_url):
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme != "https" or parsed.hostname != f"sqs.{args.region}.amazonaws.com" or not parsed.path.startswith("/" + args.expected_account + "/threatlens-"):
            raise ValueError("Queue does not belong to the expected project/account/region")
    config = output_value(outputs, "client_config")
    api_url = config["apiUrl"]
    parsed_api = urllib.parse.urlparse(api_url)
    if parsed_api.scheme != "https" or not (parsed_api.hostname or "").endswith(f".execute-api.{args.region}.amazonaws.com"):
        raise ValueError("Unexpected API endpoint")
    seed = args.seed if args.seed is not None else int(time.time())
    now = datetime.now(timezone.utc)
    samples = list(events(12, seed))
    for event in samples:
        event["time"] = now.isoformat()
        event["region"] = args.region
    findings = [detect(normalize(e)) for e in samples]
    findings = [i for i in findings if i]
    ids = [i["id"] for i in findings]
    db, eventbridge, sqs = session.client("dynamodb"), session.client("events"), session.client("sqs")
    deserialize = TypeDeserializer()
    report = {"schemaVersion": 1, "startedAt": now.isoformat(), "mode": "LIVE_AWS_SAFE_SYNTHETIC", "region": args.region,
              "seed": seed, "accountMatched": True, "nonRootIdentity": True, "expectedIncidents": len(ids), "plannedEvents": 15,
              "notificationsRequested": False, "cognitoChanges": False, "submittedEvents": 0, "checks": {}, "status": "RUNNING"}

    def persist():
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def fetch_known_items():
        keys = [{"PK": {"S": prefix + incident_id}, "SK": {"S": "META"}} for incident_id in ids for prefix in ("INCIDENT#", "OUTBOX#")]
        response = db.batch_get_item(RequestItems={table_name: {"Keys": keys, "ConsistentRead": True}})
        if response.get("UnprocessedKeys"):
            return [], False
        result = [{k: deserialize.deserialize(v) for k, v in item.items()} for item in response.get("Responses", {}).get(table_name, [])]
        return result, True

    def publish(batch):
        for start in range(0, len(batch), 10):
            chunk = batch[start:start + 10]
            if report["submittedEvents"] + len(chunk) > 15:
                raise RuntimeError("The smoke test's fifteen-event cap would be exceeded")
            report["submittedEvents"] += len(chunk)
            persist()
            response = eventbridge.put_events(Entries=[{"EventBusName": bus_name, "Source": e["source"], "DetailType": e["detail-type"], "Detail": json.dumps(e["detail"]), "Time": now} for e in chunk])
            if response["FailedEntryCount"]:
                raise RuntimeError("EventBridge rejected one or more synthetic entries")

    try:
        # Guard against accidentally testing with real notification delivery enabled.
        names = output_value(outputs, "function_names")
        notifier_name = require_project_resource(names["notifier"])
        notifier = session.client("lambda").get_function_configuration(FunctionName=notifier_name)
        if notifier.get("Environment", {}).get("Variables", {}).get("NOTIFICATIONS_ENABLED") != "false":
            raise RuntimeError("Notification worker is not configured for simulated delivery")
        report["checks"]["notificationConfiguration"] = "SIMULATED"
        try:
            urllib.request.urlopen(api_url + "/incidents", timeout=15)
            status = 200
        except urllib.error.HTTPError as exc:
            status = exc.code
        report["checks"]["unauthenticatedApiStatus"] = status
        if status != 401:
            raise RuntimeError("Unauthenticated API did not reject with 401")
        publish(samples)
        report["publishedInitial"] = len(samples)
        persist()
        observed = []
        for attempt in range(18):
            observed, complete = fetch_known_items()
            incident_count = sum(i.get("entity") == "INCIDENT" for i in observed)
            simulated_count = sum(i.get("entity") == "OUTBOX" and i.get("status") == "SIMULATED" for i in observed)
            if complete and incident_count == len(ids) and simulated_count == len(ids):
                break
            time.sleep(5)
        report["checks"]["createdIncidents"] = incident_count
        report["checks"]["simulatedOutboxRecords"] = simulated_count
        if incident_count != len(ids) or simulated_count != len(ids):
            raise RuntimeError("Expected incident and simulated-outbox records did not converge within 90 seconds")
        before = {i["id"]: int(i["version"]) for i in observed if i.get("entity") == "INCIDENT"}
        replays = [e for e in samples if detect(normalize(e))][:3]
        publish(replays)
        report["publishedReplay"] = len(replays)
        # Wait until both visible and in-flight messages have drained; approximate queue metrics alone are not proof.
        for attempt in range(12):
            time.sleep(5)
            attrs = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"])["Attributes"]
            if all(int(v) == 0 for v in attrs.values()):
                break
        observed, complete = fetch_known_items()
        after = {i["id"]: int(i["version"]) for i in observed if i.get("entity") == "INCIDENT"}
        report["checks"]["replayPreservedIdentitiesAndVersions"] = complete and before == after
        report["checks"]["replayPreservedSingleOutboxPerIncident"] = sum(i.get("entity") == "OUTBOX" for i in observed) == len(ids)
        report["checks"]["inputQueueApproximateCounts"] = {k: int(v) for k, v in attrs.items()}
        dlq = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"])["Attributes"]
        report["checks"]["dlqApproximateCounts"] = {k: int(v) for k, v in dlq.items()}
        if not report["checks"]["replayPreservedIdentitiesAndVersions"] or not report["checks"]["replayPreservedSingleOutboxPerIncident"] or any(int(v) for v in attrs.values()) or any(int(v) for v in dlq.values()):
            raise RuntimeError("Replay or queue verification did not pass")
        report["status"] = "PASS"
    except Exception as exc:
        report["status"] = "FAIL"
        # Keep account IDs/ARNs and raw AWS payloads out of the public report.
        report["failureType"] = type(exc).__name__
        if isinstance(exc, RuntimeError):
            report["failureSummary"] = str(exc)
        raise
    finally:
        report["finishedAt"] = datetime.now(timezone.utc).isoformat()
        persist()
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
