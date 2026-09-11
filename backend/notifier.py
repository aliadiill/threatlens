"""Transactional outbox with at-least-once notification delivery, never exactly-once."""
import json
import os


def handle_records(event, table, sns, topic, enabled):
    failures = []
    for record in event.get("Records", []):
        sequence = record["dynamodb"]["SequenceNumber"]
        try:
            image = record["dynamodb"].get("NewImage", {})
            if record.get("eventName") != "INSERT" or image.get("entity", {}).get("S") != "OUTBOX":
                continue
            key = {"PK": image["PK"]["S"], "SK": "META"}
            item = table.get_item(Key=key, ConsistentRead=True).get("Item", {})
            if item.get("status") != "PENDING":
                continue
            if enabled:
                sns.publish(TopicArn=topic, Subject="ThreatLens security incident", Message=json.dumps({"idempotencyKey": item["incidentId"], "incidentId": item["incidentId"], "severity": item["severity"], "title": item["title"]}))
            # A crash after publish and before this update can repeat a notification.
            table.update_item(Key=key, UpdateExpression="SET #s = :sent", ConditionExpression="#s = :pending", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":sent": "SENT" if enabled else "SIMULATED", ":pending": "PENDING"})
        except Exception:
            failures.append({"itemIdentifier": sequence})
    return {"batchItemFailures": failures}


def handler(event, context):
    import boto3
    return handle_records(event, boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"]), boto3.client("sns"), os.environ["TOPIC_ARN"], os.environ.get("NOTIFICATIONS_ENABLED") == "true")
