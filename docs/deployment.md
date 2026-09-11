# Deployment and teardown procedure

The recorded learning deployment completed its live tests and was removed. See [actual browser acceptance](live-browser.md) and [verified teardown](teardown.md). The following procedure is for an intentional future deployment.

## Prerequisites and review

Use a verified non-root role with temporary credentials. Confirm the intended account and region, account plan/service eligibility and Lambda quota. This repository defaults to no real notification, no CloudTrail input and no pipeline. The integration task can enable them explicitly.

Terraform's default backend is local to make the first reviewed deployment possible. Before team/shared use, create a separate protected, versioned S3 state bucket, use the S3 backend's `use_lockfile=true`, and migrate state with `terraform init -migrate-state`. State bootstrap is intentionally outside this application stack. Never commit state, plans, real tfvars or authentication material.

## Local checks and first infrastructure apply

```sh
npm ci
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
npm test
npm run build
python scripts/check_security.py
python scripts/package_backend.py
terraform -chdir=infra init
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
terraform -chdir=infra plan -out=reviewed.tfplan
# Inspect the account, additions, IAM, service sizes and any destructive changes.
terraform -chdir=infra apply reviewed.tfplan
```

The `lambda_reserved_concurrency` default is -1 to use the account pool. Accounts with a ten-concurrency learning quota cannot reserve per-function capacity while meeting AWS's unreserved-pool requirement. On a larger account, choose at least two per function. The SQS event-source mapping remains capped at two concurrent processors.

The archive data source preserves the `backend/` package directory; handler names are `backend.processor.handler`, `backend.api.handler` and `backend.notifier.handler`. No Docker image or native build is needed. The Python SDK is supplied by the Lambda runtime.

## Publish application

Export Terraform outputs to deployment environment variables without putting them into a committed file. In PowerShell:

```powershell
$env:FRONTEND_BUCKET = terraform -chdir=infra output -raw frontend_bucket
$env:DISTRIBUTION_ID = terraform -chdir=infra output -raw distribution_id
$env:FUNCTION_NAMES = terraform -chdir=infra output -json function_names
$env:CLIENT_CONFIG = terraform -chdir=infra output -json client_config
python scripts/deploy_application.py
```

The helper uploads the three Lambda packages, waits for function updates, writes a live public configuration, uploads assets before index.html, and invalidates the root/index/config paths. It preserves old hashed assets for cache safety and rollback. Terraform owns infrastructure; application code hashes can differ after a pipeline deployment. A later Terraform plan must use the same source revision to avoid unintentionally reverting code.

## Provision an analyst and exercise the live path

Create an analyst in the Cognito pool using the administrator console or a scoped temporary role; use an email address that I control. Do not put a password into repository configuration. Complete first sign-in, password change and TOTP enrollment in the hosted UI. Then:

1. Confirm an unauthenticated API request returns 401.
2. Publish at most twelve custom demo events with `python scripts/generate_events.py --send --count 12 --seed 7 --bus BUS_NAME`.
3. Verify queue processing, ten incidents and outbox delivery markers. Benign signals should not create incidents.
4. Replay the same seed. Incident/outbox counts should remain unchanged.
5. Sign in, inspect an incident, save an investigation note, resolve it, refresh and confirm persistence.
6. Exercise an intentionally malformed **custom test** message only in the project queue and verify DLQ behavior. Never call dangerous AWS APIs to generate a sample.
7. Record actual timestamps, service result identifiers, screenshots and outcomes in the evidence document.

The initial browser fixture has fixed dates. A live sent event uses the same explicit fixture time; a “today” metric will not count historical samples. Change the sample seed to create independent identities, not to imitate recent live attacks.

## Teardown

Disable pipeline/event generation, stop upstream forwarding, and decide whether to export incident evidence. Review `terraform plan -destroy` for this project alone. Versioned S3 buckets must have object versions/delete markers explicitly removed before Terraform can delete them; no blanket account-cleanup command is supplied.

Destroy the reviewed application stack, wait for CloudFront disable/delete completion, and verify queues, database, functions, buckets, alarms, pipeline and build projects are gone. The KMS key enters a seven-day pending-deletion period. Cognito users are removed with the application pool. Preserve the separate state backend and any shared CodeConnections resource; this stack does not own the supplied connection.

Cost reconciliation can lag. Check billed service/region usage after removal rather than treating a successful destroy command as proof that no account cost remains.
