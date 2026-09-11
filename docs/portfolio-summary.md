# Portfolio summary

**ThreatLens — Cloud security detection and investigation workspace**

Built an event-driven cloud-security application with Python detection rules, a TypeScript/React analyst dashboard, DynamoDB incident/timeline persistence, and a transactional notification outbox. Terraform defines EventBridge, SQS/DLQ, Lambda, Cognito-authenticated HTTP APIs, private S3/CloudFront hosting, encryption, alarms and an optional AWS CodePipeline/CodeBuild workflow.

The local demonstration distinguishes synthetic events from AWS traffic. It covers five meaningful signal categories, incident filtering/details, notes, status transitions and safe simulated response guidance. Offline tests exercise duplicate delivery, partial failures, stale writes, pagination and the at-least-once notification failure window.

This summary describes implemented code and local evidence. Add claims of deployed availability, actual pipeline execution or measured cloud performance only after the integration evidence supports them.

Suggested repository description: “AWS security incident workflow: EventBridge/SQS, idempotent Lambda detection, DynamoDB outbox, Cognito React dashboard, Terraform and CodePipeline.”

