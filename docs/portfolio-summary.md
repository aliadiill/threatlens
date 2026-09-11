# Portfolio summary

**ThreatLens — Cloud security detection and investigation workspace**

Built an event-driven cloud-security application with Python detection rules, a TypeScript/React analyst dashboard, DynamoDB incident/timeline persistence, and a transactional notification outbox. Terraform defines EventBridge, SQS/DLQ, Lambda, Cognito-authenticated HTTP APIs, private S3/CloudFront hosting, encryption, alarms and an optional AWS CodePipeline/CodeBuild workflow.

The local demonstration distinguishes synthetic events from AWS traffic. It covers five meaningful signal categories, incident filtering/details, notes, status transitions and safe simulated response guidance. Offline tests exercise duplicate delivery, partial failures, stale writes, pagination and the at-least-once notification failure window.

A bounded live AWS smoke test also passed: fifteen safe custom-event submissions produced the ten expected incident/outbox pairs, repeat deliveries preserved incident identity/version, outboxes remained SIMULATED, and the unauthenticated API rejected access. The test completed in approximately eighteen seconds including its polling; this is a single smoke-run duration, not a latency benchmark or service-level objective. The corrected application pipeline then passed Source, Quality, Review and Deploy for revision ecd9440 at 06:19:47 UTC on 11 September 2026; see [its runtime evidence](pipeline-result.json). I verified required Cognito MFA, PKCE sign-in, a status/note persisted after API refresh/reopen and sign-out. [Browser evidence](live-browser.md) includes actual screenshots and the verified permanent GitHub Pages demo. Teardown status has a separate verification record.

Suggested repository description: “AWS security incident workflow: EventBridge/SQS, idempotent Lambda detection, DynamoDB outbox, Cognito React dashboard, Terraform and CodePipeline.”
