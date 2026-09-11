# AWS service choices

| Service | Problem solved | Tradeoff and alternative |
| --- | --- | --- |
| EventBridge | Routing and separation of safe demonstrations from existing security events | Event patterns are routing, not detection rules. Direct SQS publishing is simpler but teaches less about cloud event integration. |
| SQS + DLQ | Durable buffering, backpressure and retry isolation | Standard delivery may duplicate and reorder; DynamoDB conditional writes handle duplicate incident creation. |
| Lambda | Low-volume validation, classification, API and outbox processing | Cold starts and shared account concurrency; no always-on server or NAT needed. |
| DynamoDB | Atomic incident/timeline/outbox storage and consistent detail reads | Access patterns must be designed up front. The single feed index is a lab-scale choice. |
| SNS + KMS | Optional fanout and encrypted notification storage | Customer-managed key and notifications have cost. The default worker records SIMULATED and does not send messages. |
| HTTP API | HTTPS routes, throttling, CORS and JWT authorization | Fewer gateway features than REST API; sufficient for the three incident routes. |
| Cognito | Hosted sign-in, PKCE, access-token scopes and mandatory TOTP MFA | Provisioned analysts share a workspace. No custom password implementation. |
| S3 + CloudFront | Private static origin, HTTPS edge delivery and browser security headers | Distribution deployment/changes are slower than a local web server. |
| CloudWatch | Retained logs and queue/function alarms | Partial record failures may not increment Lambda Errors, so DLQ/age metrics also matter. |
| CodePipeline + CodeBuild | GitHub-triggered testing, review and application publication | Infrastructure apply remains a separate reviewed action with broader permissions. |
| CloudTrail, optional existing input | Real administrative-event provenance | The project does not activate billable security products or claim to collect every event type. |

No VPC, NAT gateway, EC2 fleet, RDS database, OpenSearch cluster, GuardDuty detector or Security Hub hub is required for this bounded implementation. A larger SOC could integrate those sources after agreeing on detection needs and costs.

