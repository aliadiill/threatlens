# GitHub → CodePipeline → CodeBuild

## Source and permissions

Set `enable_pipeline=true`, a user-supplied existing AVAILABLE `connection_arn`, `repository_id=owner/threatlens`, and the intended branch. The connection must be authorized for that repository in the GitHub App installation. Do not commit the real ARN or account identifier. Terraform creates the pipeline, artifact storage and scoped service roles, not the GitHub connection.

The CodePipeline source action uses `CodeStarSourceConnection` (the action provider retains its historical name). CodeConnections is the modern connection service. The IAM policy supports the relevant connection action names and scopes them to the supplied ARN. See [AWS source action documentation](https://docs.aws.amazon.com/codepipeline/latest/userguide/action-reference-CodestarConnectionSource.html).

## Release stages

1. **Source:** GitHub changes produce an immutable source artifact.
2. **Quality:** CodeBuild installs locked frontend dependencies, Python test/audit dependencies and checksum-verified Terraform; runs the thirty-three backend/deployment and seven frontend tests; type-checks/builds the SPA; audits dependencies; checks explicit source guardrails; and formats/validates Terraform. Any failed command fails the stage.
3. **Review:** A manual CodePipeline approval exposes the concrete built revision before publication. It is an application release control, not a request to repeat previously granted local coding permission.
4. **Deploy:** A separate scoped CodeBuild role receives only the built artifact, updates the application functions, publishes static content/config and invalidates CloudFront. It has no broad infrastructure or IAM permissions.

The V2 pipeline uses QUEUED execution to prevent overlapping application deployments. Build/queue timeouts are bounded, privileged mode is off, logs retain fourteen days, and versioned artifact objects expire after fourteen days.

The npm lock was generated with `legacy-peer-deps=true` after an npm dependency-tree resolver bug. The checked-in .npmrc makes `npm ci` use the same resolution mode. TypeScript, tests, build and dependency audit still gate compatibility/security.

## Infrastructure changes

Terraform plan/apply is separate because it requires broader permissions than publishing application code. Validate runs in CI. An operator reviews and applies the infrastructure plan using the same revision before enabling/releasing application changes. This avoids granting a GitHub-triggered application role administrator rights.

## Failure and rollback

A quality failure prevents approval/deployment. A deployment can partially update Lambda functions before a later step fails; this is not an atomic blue/green release. Redeploy the last known good build artifact to restore code and frontend, then rerun authenticated smoke tests. S3 versioning and retained hashed assets aid recovery. DynamoDB backward-compatible schema changes are required across releases.

A production extension would add published Lambda versions/aliases, canary traffic shifting, automated rollback alarms, signed artifacts and integration-test gates. Do not describe those as implemented here. No repository file by itself proves the pipeline has executed; record the actual execution outcome separately.

## Verified first deployment failure and correction

The first live pipeline reached Deploy after Source, Quality and Review succeeded. At 05:58:10 UTC on 11 September 2026, CodeBuild failed while waiting for the first Lambda update: the FunctionUpdatedV2 waiter called lambda:GetFunction, which the scoped deploy role did not allow. The earlier code update had succeeded; frontend uploads had not begun, explaining the empty-origin 403.

The correction uses the FunctionUpdated waiter, which polls GetFunctionConfiguration already allowed on the three project functions. It waits up to ninety two-second checks per function and stops on failed/timed-out updates. IAM permissions were not widened. Three offline tests exercise the actual SDK waiter with stubbed AWS responses: in-progress-to-success, failure before the next function, and bounded timeout. See the [AWS waiter reference](https://docs.aws.amazon.com/boto3/latest/reference/services/lambda/waiter/FunctionUpdated.html).

Release this correction through a new source/build artifact. Retrying the old Deploy artifact would still execute its old waiter. A subsequent successful live release must be recorded separately; a local fix alone does not prove that release succeeded.
