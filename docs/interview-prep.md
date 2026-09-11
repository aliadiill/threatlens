# Interview preparation

## Thirty seconds

ThreatLens is an explainable cloud-security incident workflow. EventBridge sends safe demo or selected CloudTrail events to SQS; a Python Lambda classifies them and atomically writes the incident, history and notification intent to DynamoDB. Analysts use a Cognito-protected React dashboard to investigate and document decisions. Responses are simulated, and duplicate/retry semantics are tested.

## One minute

The interesting engineering problem is preserving correct state despite retries and human concurrency. SQS can redeliver, so incident identity comes from the original event and rule; a conditional transaction creates the incident and outbox once. A DynamoDB stream drives notifications, with an explicit at-least-once publish/marker gap. Analysts submit a version with each edit, so concurrent updates return a conflict instead of losing notes. Terraform defines the managed services and scoped roles, while CodePipeline/CodeBuild tests and publishes application artifacts through a review stage.

## Five-minute structure

Start with the business requirement: understandable signals and retained investigation decisions. Walk one administrator-policy event through validation, SQS buffering, rule classification, idempotent transaction and outbox. Show the dashboard, incident guidance, timeline and resolution note. Explain authentication and why public HTTPS endpoints still require authorization. Demonstrate a duplicate event and a stale analyst update. Finish with CI/CD, cost controls, current test evidence, and the production boundaries below.

## Technical questions

**Why SQS between EventBridge and Lambda?** It provides explicit buffering, controllable processing concurrency, partial failure and poison-message handling. Direct targets are simpler but do not expose this workload's queue/retry tradeoffs.

**Is it exactly once?** Incident creation is conditionally idempotent while its records remain stored. Delivery is at least once. A notification can repeat if publish succeeds but the delivery marker write fails; a test makes that visible.

**How do you avoid false claims of compromise?** Rules are narrow and explainable. Failed login is a medium signal, read-only activity is benign, and denied privilege changes are not presented as successful escalation. Real-world correlation and suppression would be additional work.

**Why an outbox rather than calling SNS during detection?** The transaction preserves both incident and notification intent. Without it, one system could succeed while the other fails with no durable recovery record.

**What does a 409 mean?** The incident's version changed after the analyst read it. The interface prompts a refresh/retry rather than overwriting another decision.

**Why no VPC/NAT?** The dependencies are managed AWS services. Identity/resource policies and HTTPS define the boundaries, and a NAT gateway would add cost without meeting a stated requirement here.

**How does the pipeline limit damage?** Test and deploy roles are separate. The app publisher can update only its functions/static site and cannot create infrastructure or change IAM. Infrastructure plans are reviewed separately.

**What fails under significant scale?** The constant feed-index partition can become hot. A huge timeline can exceed synchronous response size. There is no outbox sweeper or multi-tenant isolation. These are concrete extensions, not hidden production claims.

**What would you test next in AWS?** Unauthenticated rejection, hosted MFA sign-in, twelve-event ingestion, duplicate replay, note/status persistence, DLQ recovery, disabled/authorized notifications, alarm transitions, PITR restore and an actual failing/successful pipeline execution.

**What can you honestly claim now?** Describe source and locally executed tests. Only cite live deployment, recovery and pipeline execution after their actual evidence is recorded.

