# Architecture and reliability

## Business problem

A small cloud team needs an explainable way to turn suspicious administrative activity into incidents and preserve investigation decisions. A raw log entry has neither triage status nor a human explanation. ThreatLens adds a deterministic classification, stable incident identity, resource context, an append-only timeline, and a safe response checklist.

This is a learning SOC, not a production SIEM. It has five narrow rules: successful audit-logging removal, successful administrator-policy attachment, successful public exposure of SSH/RDP or all ports, failed console sign-in, and successful long-lived access-key creation. A single login failure is a medium-priority signal, never a claim of account compromise. Read-only API calls and public HTTPS alone are benign under this rule set.

## End-to-end ingestion

1. The bounded generator publishes custom `threatlens.demo` events to a dedicated bus. Optional forwarding accepts selected existing CloudTrail event sources from the default bus. Enabling the forwarding variable does not create a CloudTrail trail.
2. The bus sends to an encrypted standard SQS queue. An explicit queue policy permits only the ingestion rule. EventBridge target delivery failures go to the DLQ.
3. Lambda receives batches of up to ten. Each record is validated, normalized and classified independently. Returning `ReportBatchItemFailures` retries only failed records.
4. The detector computes a stable 96-bit identifier from source, original event identity and rule category. A transaction conditionally creates incident metadata, the initial timeline entry and the notification outbox record together.
5. A duplicate event finds an existing incident and produces no second transaction/outbox. Other transaction failures propagate for retry. No raw CloudTrail event body or credential-bearing request structure is persisted.
6. A filtered DynamoDB stream invokes the notification worker only for newly inserted outbox records. Notifications default to SIMULATED. Opt-in SNS publishes contain an incident idempotency key, severity and title.

## Data model

| Item | Partition key | Sort key | Purpose |
| --- | --- | --- | --- |
| Incident metadata | INCIDENT#id | META | Severity, resource, classification, source, status and optimistic version |
| Timeline entry | INCIDENT#id | EVENT#timestamp#unique-id | Immutable detection/analyst history |
| Outbox | OUTBOX#id | META | PENDING, SIMULATED or SENT delivery marker |

The `timeline` GSI indexes only incident metadata with a constant incident partition and timestamp/id sort key. Listing uses a bounded fifty-item page and returns a cursor. The UI counts the loaded view and labels this explicitly. GSI reads are eventually consistent; refresh after ingestion or changes. Incident detail uses consistent reads and follows DynamoDB pagination across its one-megabyte query boundary.

A single GSI partition is appropriate for a low-volume shared SOC. At high ingestion volume, shard the feed index and introduce tenant boundaries. Very large incident timelines can eventually exceed the synchronous API payload limit even though database pagination is correct; cursor-based timeline endpoints and export to S3 are the next extension.

## Analyst workflow

Cognito issues access tokens through authorization code plus PKCE. API Gateway validates the issuer, audience and per-route scope. Lambda additionally requires `token_use=access` and a subject claim. All administrator-provisioned analysts share one SOC workspace; this is not a multi-tenant product.

An update carries the version read by the analyst. The transaction changes metadata only if that version still matches and appends the note/status history atomically. Stale edits return 409 instead of silently overwriting another analyst. Resolution requires a note. Reopening a resolved incident passes through INVESTIGATING.

## Retry and notification guarantees

SQS and DynamoDB Streams are at-least-once sources. The transaction guarantees one incident and one initial outbox per event/rule identity while those records remain stored. It does **not** guarantee exactly-once email.

The notifier publishes to SNS, then marks the outbox SENT. If it crashes between those steps, the retry can publish again. The unit suite deliberately exercises this gap. Downstream automated consumers should deduplicate the included incident identity. Email recipients can receive repeats. Marking SENT before publishing would create the opposite, worse failure: a lost notification.

Processing poison records retries five receives before the input DLQ. Notification stream retries are limited to five attempts and one hour record age, with bisection and a separate failure queue. Stream failure destinations may contain pointer metadata; the persistent outbox is the recovery source. The outbox has no sweeper: operators must investigate PENDING records and replay them through a reviewed recovery operation before stream retention expires.

## Safe response boundary

The automated response is a prepared investigation checklist. It never applies containment to AWS resources. This is enforced by both the code and the detector/notifier IAM policies. Real response automation would need separate response roles, approvals, resource targeting, action idempotency, rollback and integration tests.

Primary references: [SQS partial failures](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html), [event-source delivery semantics](https://docs.aws.amazon.com/lambda/latest/dg/invocation-eventsourcemapping.html), [DynamoDB stream failure retention](https://docs.aws.amazon.com/lambda/latest/dg/services-dynamodb-errors.html).

