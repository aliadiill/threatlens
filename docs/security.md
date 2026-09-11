# Security model

## Identity and browser access

Cognito sign-up is administrator-only. Passwords have a fourteen-character minimum with mixed classes, temporary passwords expire after one day, and TOTP MFA is mandatory. Hosted authorization-code sign-in uses a random state and PKCE verifier. The verifier/state temporarily reside in session storage; access tokens remain in memory and expire after fifteen minutes. Reloading a live page therefore requires a new sign-in flow; hosted SSO can make that brief.

API Gateway enforces the Cognito issuer, web-client audience and read/write route scopes. API code rejects ID tokens and missing subjects. CORS permits the deployed frontend origin only. CORS is a browser policy, not the authorization control. Notes render through React text escaping; raw HTML is never inserted.

All authorized analysts can read and update all incidents in this shared learning SOC. Claiming tenant isolation or fine-grained role separation would be inaccurate. Add explicit groups/tenant keys and authorization tests before a multi-tenant use case.

## Least privilege

Processor roles read only their SQS queue and write/read only the incident table. The API can query the incident feed and read/update incident-partition items; it has no outbox publishing rights. The notifier reads the one table stream and outbox partitions, publishes only to the project SNS topic, and writes its failure queue. The only broad DynamoDB resource is `ListStreams`, an enumeration permission; stream read operations are ARN-scoped.

No workload role receives IAM mutation, EC2 termination or security-group mutation permissions. CI test and deployment roles are separate. The deploy role can update only the three application functions, publish to the frontend bucket, and invalidate the one distribution. It cannot apply Terraform or change IAM.

EventBridge receives resource-policy permission on the project queue scoped to the specific rule. CloudFront signs origin requests with OAC; the S3 read grant is limited to that distribution. Buckets block public access and deny insecure transport.

## Data handling and encryption

SQS uses service-managed encryption; DynamoDB server-side encryption and seven-day point-in-time recovery are enabled. S3 uses SSE-S3, versioning and bounded noncurrent-version retention. SNS uses a rotating customer-managed KMS key. CloudWatch logs retain fourteen days. AWS transport endpoints use HTTPS.

The detector stores an allowlisted summary rather than raw CloudTrail request bodies. Never place secrets in investigation notes. Log failures include message identity and exception class, not source payloads. Terraform state can contain private settings such as notification email and must remain outside Git in protected storage.

CloudFront adds content-type protection, framing denial, HSTS, referrer policy and a CSP. Styles allow inline values for small chart widths. The frontend uses system fonts and does not require a third-party font service. The distribution's default AWS certificate supplies HTTPS without a domain. AWS uses the TLSv1 security policy for that default certificate and ignores a stricter minimum supplied in configuration; the code records TLSv1 to avoid perpetual drift. **This hostname does not enforce a TLS 1.2 minimum.** A production requirement for a modern minimum needs a custom hostname, an appropriate ACM certificate and a supported stricter CloudFront policy. No domain was purchased for the learning deployment.

## Review and remaining work

The source guardrail checks for credential-like patterns, unsafe HTML insertion and destructive response APIs. It complements dependency audits and manual IAM review; it is not a full secret scanner, penetration test or compliance certification. Production work includes independent IAM analysis, adversarial API testing, WAF/rate-abuse review, scoped analyst roles, alert-source validation and incident-retention policy.

Primary reference: [API Gateway JWT validation and scopes](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html).
