# Cost model and boundaries

No cloud deployment cost is incurred by running the checked-in browser demo or the offline unit tests. AWS integration creates billable resources and requests even when credits may cover them. Check current account eligibility, credit scope/expiry and service prices before applying a plan; credits are not a spending limit.

The user's hard limit is no personal out-of-pocket charges and at most USD 100 in total promotional credits across the portfolio, not per month. Preserve the existing Free plan; do not upgrade it to enable a blocked service. Use short, bounded integration tests and remove billable demonstration resources afterward. Stop if plan eligibility or credit coverage cannot be established. Pricing alarms alone cannot enforce this requirement.

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
