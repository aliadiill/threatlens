# Monitoring and operations

The infrastructure creates input/notification DLQ alarms, per-function error alarms and an input-queue oldest-message alarm. They have no outbound alarm actions by default, so they are visible in CloudWatch without messaging an unauthorized recipient. Configure an approved operations destination separately.

| Signal | Expected observation | Operator action |
| --- | --- | --- |
| Input queue depth/age | Drains after a bounded demo; oldest age below five minutes | Inspect processor throttles/errors and event shape. Do not raise throughput blindly. |
| Input DLQ visible messages | Zero | Inspect metadata safely, fix validation/storage problem, then redrive only the intended messages. Duplicates are safe for incident creation. |
| Notification failure queue | Zero | Inspect the stream failure metadata and the PENDING outbox. Correct IAM/SNS/KMS issue before a reviewed retry. |
| Lambda Errors/Throttles | No unexpected growth | Correlate with queue age and account concurrency. |
| Processor structured log action | incident-created, duplicate-suppressed or record-failed | Use incident/message identity, never paste raw security payloads into public documentation. |
| DynamoDB transaction conflicts | Occasional analyst version conflict is expected | Refresh a 409 rather than overwrite another analyst. Persistent ingestion failures require investigation. |
| API status/latency | Auth failures understood; successful reads/updates | Check token expiry, scopes and source configuration before widening access. |
| Outbox status | SIMULATED by default; SENT only when opt-in publishes succeed | A PENDING item can survive a stream delivery failure; reconcile it manually. |

Per-record partial failures do not necessarily increment the Lambda invocation Errors metric. Queue redrive, age and DLQ alarms are therefore essential. The source guardrail and unit suite do not replace an end-to-end alarm delivery test.

Logs retain fourteen days and record safe operational metadata. DynamoDB has seven-day PITR; test a restore into a separate table, inspect its contents through authorized access, and repoint a reviewed deployment before relying on recovery. Retention and storage still incur cost. No live restore, alarm transition or notification delivery is claimed by these runbooks.

