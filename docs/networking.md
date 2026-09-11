# Networking and trust boundaries

The browser retrieves public static assets through CloudFront HTTPS. S3 remains private and accepts content reads through the distribution's signed origin requests. Application data is never embedded into static assets.

The free CloudFront default hostname uses AWS's default-certificate TLSv1 policy. HTTPS redirection and HSTS are configured, but this deployment does not claim to reject all legacy TLS clients. Enforcing a newer minimum requires a custom hostname/certificate and an explicitly supported policy.

The browser calls a regional API Gateway HTTPS endpoint with a short-lived Cognito access token. API Gateway invokes the API Lambda using a resource permission scoped to the gateway execution ARN. The gateway permits the CloudFront origin in CORS. It is publicly addressable but authenticated; no security group is used to pretend that a public API is private.

Lambda, SQS, DynamoDB and EventBridge use AWS-managed service networking. Functions are not attached to a VPC, so no NAT gateway, public instance IP or subnet routing is needed. This deliberately avoids the extra cost and operational burden of a network tier that would not protect these managed services. Private VPC endpoints would become relevant if the deployment's network/compliance requirements changed.

us-east-1 is the primary region for this learning implementation and simplifies support for IAM/global administrative CloudTrail events and the selected services. A Canadian deployment needs source-region routing, service availability and data-residency analysis; changing one region variable does not establish regulatory compliance. CloudFront is global; dynamic incident data remains in the regional API/database path.
