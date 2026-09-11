# Troubleshooting

**Dashboard shows demo data after deployment.** Verify dist/config.json was overwritten with the Terraform client_config output, uploaded with no-store caching and invalidated. The checked-in configuration intentionally defaults to demo. Do not hide the demo banner to imply a live integration.

**Live login loops or code exchange fails.** Check the exact HTTPS callback/logout origin including trailing slash, Cognito domain/client and OAuth scopes. The browser validates random state and PKCE; avoid replaying an old callback. Check system clock. Live access tokens are in memory, so reload initiates another login.

**API returns 401/403.** Use a Cognito access token, not an ID token. Confirm issuer/client audience, token expiry and threatlens/read or threatlens/write scope. Do not disable JWT authorization to make an error disappear.

**Update returns 409.** Another write changed the incident version. Refresh the detail, retain your note locally, and deliberately reapply the update against the current state.

**Events never produce incidents.** Check region, dedicated bus name, rule match, SQS policy, event source mapping and detector logs. DescribeInstances is intentionally benign. Denied privileged mutations are not treated as successful changes. CloudTrail input forwarding does not enable a trail or collect every region.

**Queue retries indefinitely or reaches DLQ.** Inspect message identity and exception class. Check resource policies, DynamoDB transaction rights and malformed event shape. Do not log full CloudTrail parameters. Repair the cause before redrive; repeated valid event IDs are deduplicated.

**Duplicate emails.** The notifier is at least once: publish can succeed before marking SENT fails. Deduplicate automated consumers with incidentId. Email can repeat; this is explicitly tested and documented.

**Terraform cannot reserve Lambda capacity.** Small learning accounts may have ten total concurrent executions. Keep lambda_reserved_concurrency=-1 and SQS mapping concurrency=2; do not request expensive service changes just to match a production-sized default.

**Local SDK appears as an empty namespace / esbuild denies a parent directory.** On restricted Windows hosts, packages installed outside the process's permitted ACL can be unreadable. Run the local test/build with appropriate authorized filesystem access. This is not evidence of an AWS problem.

**npm reports edgesOut while resolving peers.** The checked-in .npmrc uses the resolver workaround that produced the lock. Use npm ci with that file. Do not force-update all packages blindly; run tests/build/audit after a deliberate version change.

**Destroy fails on a bucket.** S3 versioning retains object versions and delete markers. Inspect and empty the exact project bucket through an explicit reviewed action, then retry. Never substitute recursive deletion across all account buckets.

**First DynamoDB apply reports a KMS key not found.** During this deployment, the initial table-create request returned KMS NotFound; a subsequent key check reported enabled, and the reviewed retry succeeded without reducing encryption. That sequence is consistent with first-use propagation, although the sequence alone does not prove the root cause. Inspect the specific key/service state and failed plan before retrying; do not disable encryption as a blanket workaround.
