# Cost model and boundaries

No cloud deployment cost is incurred by running the checked-in browser demo or the offline unit tests. AWS integration creates billable resources and requests even when credits may cover them. Check current account eligibility, credit scope/expiry and service prices before applying a plan; credits are not a spending limit.

I aimed to keep all three projects within a one-time $100 AWS credit budget. I used the Free plan, ran short integration tests, and removed the demonstration resources after collecting evidence. I kept the public previews on GitHub Pages so the portfolio stays available without an always-running AWS lab. Budget alerts help with visibility; they are not a hard spending cap.

## Main cost drivers

| Component | Driver | Bound/control |
| --- | --- | --- |
| Lambda | Invocation count and GB-seconds | 256 MB, thirty-second timeout, SQS mapping concurrency two, finite generator |
| DynamoDB | On-demand writes/reads, storage and PITR | Twelve-event demos; seven-day recovery window; incident/outbox retention is persistent |
| EventBridge/SQS | Events and queue requests | Generator accepts one to one hundred events; retry limits and fourteen-day DLQ retention |
| CloudFront/S3 | Requests, transfer, assets and retained versions | Static bundle; no NAT or running instance; old object versions expire after seven days |
| SNS/KMS | Publishes, optional delivery and customer-managed key | Real notifications disabled; one rotating project key |
| CloudWatch | Logs, alarms and detailed API metrics | Fourteen-day log retention; small explicit alarm set |
| CodeBuild/CodePipeline | Build minutes and pipeline executions | Small nonprivileged build, fifteen-minute timeout, queued releases and review stage |
| Cognito | Active users and configured features | Administrator-created analyst accounts only |

Compute a demonstration estimate from the reviewed plan using the AWS Pricing Calculator and current primary-region prices. Record the planned duration, expected event count, build count and cleanup time. No unverified dollar estimate is presented as an actual bill.

Leaving the project “idle” can still cost money through KMS key ownership, alarms, stored objects/logs/incidents, PITR and pipeline activity. The absence of EC2 does not mean zero recurring cost.

## Teardown evidence

Follow the deployment guide's scoped destroy workflow and retain source/tests/diagrams. Verify service removal after apply/destroy, then reconcile billing after reporting delay. Preserve any separate state backend, shared CodeConnections connection and account administration. Do not remove shared resources merely because this project is finished.

Scale-sensitive improvements include batched writes only where atomicity remains correct, sharded feed indexes, explicit incident archival, lower-cost log categories and reviewed alarm consolidation. These are tradeoffs to evaluate with measured usage, not reasons to weaken authentication or skip retry handling.

## Actual learning-stack removal

After live acceptance, the reviewed Terraform plan removed 75 managed resources. Independent AWS checks verified the live services absent, with the notification KMS key scheduled for deletion and a service-created DynamoDB SYSTEM backup retained to its returned expiry. Both remaining retention states have documented no-additional-storage-cost treatment; see the sources and exact results in [verified teardown](teardown.md). The permanent browser-only Pages sample remains available. This does not replace portfolio-wide reconciliation of earlier metered usage.
