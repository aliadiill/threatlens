"""DynamoDB persistence; metadata, timeline and outbox creation are atomic."""
import base64
import json
import os
import uuid
from .domain import timestamp


class Conflict(Exception):
    pass


class NotFound(Exception):
    pass


class Repository:
    def __init__(self, client=None, table=None):
        import boto3
        from boto3.dynamodb.types import TypeSerializer, TypeDeserializer
        self.client = client or boto3.client("dynamodb")
        self.table = table or os.environ["TABLE_NAME"]
        self.serializer, self.deserializer = TypeSerializer(), TypeDeserializer()

    def encode(self, item):
        return {k: self.serializer.serialize(v) for k, v in item.items()}

    def decode(self, item):
        return {k: self.deserializer.deserialize(v) for k, v in item.items()}

    def put(self, item, condition=None):
        operation = {"TableName": self.table, "Item": self.encode(item)}
        if condition:
            operation["ConditionExpression"] = condition
        return {"Put": operation}

    def create(self, incident):
        pk = "INCIDENT#" + incident["id"]
        meta = {**incident, "PK": pk, "SK": "META", "entity": "INCIDENT", "GSI1PK": "INCIDENT", "GSI1SK": incident["createdAt"] + "#" + incident["id"]}
        timeline = {"PK": pk, "SK": "EVENT#" + timestamp() + "#created", "entity": "TIMELINE", "at": timestamp(), "kind": "DETECTED", "actor": "detector", "text": incident["response"]}
        outbox = {"PK": "OUTBOX#" + incident["id"], "SK": "META", "entity": "OUTBOX", "status": "PENDING", "incidentId": incident["id"], "severity": incident["severity"], "title": incident["title"], "createdAt": timestamp()}
        try:
            self.client.transact_write_items(TransactItems=[self.put(meta, "attribute_not_exists(PK)"), self.put(timeline), self.put(outbox, "attribute_not_exists(PK)")])
            return True
        except self.client.exceptions.TransactionCanceledException:
            # A failed transaction may be contention, permissions or throttling, not a duplicate.
            existing = self.client.get_item(TableName=self.table, Key=self.encode({"PK": pk, "SK": "META"}), ConsistentRead=True)
            if existing.get("Item"):
                return False
            raise

    def list(self, cursor=None):
        args = {"TableName": self.table, "IndexName": "timeline", "KeyConditionExpression": "GSI1PK = :pk", "ExpressionAttributeValues": self.encode({":pk": "INCIDENT"}), "ScanIndexForward": False, "Limit": 50}
        if cursor:
            try:
                key = json.loads(base64.urlsafe_b64decode(cursor).decode())
                if set(key) != {"PK", "SK", "GSI1PK", "GSI1SK"} or key["GSI1PK"] != "INCIDENT" or key["SK"] != "META":
                    raise ValueError()
                args["ExclusiveStartKey"] = self.encode(key)
            except Exception as exc:
                raise ValueError("Invalid pagination cursor") from exc
        result = self.client.query(**args)
        next_cursor = base64.urlsafe_b64encode(json.dumps(self.decode(result["LastEvaluatedKey"])).encode()).decode() if result.get("LastEvaluatedKey") else None
        return {"items": [self.decode(i) for i in result["Items"]], "nextCursor": next_cursor}

    def get(self, incident_id):
        args = {"TableName": self.table, "KeyConditionExpression": "PK = :pk", "ExpressionAttributeValues": self.encode({":pk": "INCIDENT#" + incident_id}), "ConsistentRead": True}
        items = []
        while True:
            result = self.client.query(**args)
            items.extend(self.decode(i) for i in result["Items"])
            if not result.get("LastEvaluatedKey"):
                break
            args["ExclusiveStartKey"] = result["LastEvaluatedKey"]
        meta = next((i for i in items if i["SK"] == "META"), None)
        if not meta:
            raise NotFound()
        return {**meta, "timeline": sorted([i for i in items if i["entity"] == "TIMELINE"], key=lambda i: i["SK"])}

    def change(self, incident_id, version, status, note, actor):
        now = timestamp()
        values = {":expected": version, ":next": version + 1, ":now": now, ":status": status}
        update = {"TableName": self.table, "Key": self.encode({"PK": "INCIDENT#" + incident_id, "SK": "META"}), "UpdateExpression": "SET #s = :status, updatedAt = :now, version = :next", "ConditionExpression": "version = :expected", "ExpressionAttributeNames": {"#s": "status"}, "ExpressionAttributeValues": self.encode(values)}
        event = {"PK": "INCIDENT#" + incident_id, "SK": "EVENT#" + now + "#" + str(uuid.uuid4()), "entity": "TIMELINE", "at": now, "actor": actor, "kind": "ANALYST_UPDATE", "text": note or "Status changed to " + status, "status": status}
        try:
            self.client.transact_write_items(TransactItems=[{"Update": update}, self.put(event)])
        except self.client.exceptions.TransactionCanceledException as exc:
            raise Conflict("Incident changed; refresh and retry") from exc
        return self.get(incident_id)
