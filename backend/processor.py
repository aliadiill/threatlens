import json
import logging
from .domain import normalize, detect
from .repository import Repository

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def process_batch(event, repository):
    failures = []
    for record in event.get("Records", []):
        try:
            signal = normalize(json.loads(record["body"]))
            incident = detect(signal)
            if incident:
                created = repository.create(incident)
                logger.info(json.dumps({"action": "incident-created" if created else "duplicate-suppressed", "incidentId": incident["id"], "severity": incident["severity"]}))
        except Exception as exc:
            # Do not log event bodies or credential-bearing CloudTrail parameters.
            logger.error(json.dumps({"action": "record-failed", "messageId": record.get("messageId"), "errorType": type(exc).__name__}))
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}


def handler(event, context):
    return process_batch(event, Repository())
