# ThreatLens build journal: difficulties, fixes and evidence

This journal records problems encountered while building and integrating ThreatLens on 11 September 2026 UTC. It distinguishes executed failures, code-review findings, observed service behavior and remaining work. It is not a manufactured list of production incidents.

The project boundary remained constant: safe synthetic demonstrations, no destructive response calls, notifications disabled, a shared learning SOC, and no personal charges. The user permits at most USD 100 in **total promotional credits across the portfolio**, not monthly spend. Keeping the account's Free plan and removing billable demos after tests remain deployment responsibilities.

## 1. Serverless correctness needed more than a happy-path demo

**Difficulty.** SQS can retry an event; the database and SNS can fail independently; two analysts can edit the same incident. A simple “create incident then publish” sequence could duplicate incidents, lose notification intent or overwrite investigation notes.

**Implementation.** The detector derives a stable incident identifier from the original source/event/rule. A DynamoDB transaction creates incident metadata, initial timeline and outbox together. Analyst writes include a version and append history in the same transaction. The SQS handler returns partial batch failures.

**Verification.** Offline tests verified duplicate suppression, retry on storage failure, independent failed records, stale edit conflicts and atomic write shape. The live smoke submitted twelve initial events and three replays: ten expected incidents and ten SIMULATED outboxes appeared; replay preserved the known incident identities/versions; observed input/DLQ counts were zero. See [the actual runtime report](live-smoke-result.json).

**Remaining.** That smoke used safe custom events, not hostile real account activity. It did not induce a poison-message DLQ recovery or measure sustained throughput.

## 2. An outbox does not make email exactly once

**Difficulty.** Publishing a message and marking its database record SENT cannot be one transaction across DynamoDB and SNS. A crash after publish but before marking SENT can cause a repeat.

**Decision.** Preserve durable intent and document at-least-once delivery. Each notification carries an incident idempotency key. The default worker marks SIMULATED and never publishes. No handler was granted containment permissions.

**Verification.** A fault test intentionally made the post-publish marker fail and observed two publishes across retry. This was an expected semantic limit, not a passing test incorrectly interpreted as exactly-once delivery. Separate tests verify skipped SENT records and no publish when notifications are disabled.

**Remaining.** An automated downstream consumer needs deduplication. Email can repeat. A production outbox sweeper/recovery operation is not implemented; PENDING items require reviewed operator reconciliation.

## 3. A single DynamoDB Query could truncate incident history

**Finding type: code review before live integration.** The initial detail read issued only one Query, which could omit timeline entries beyond DynamoDB's one-megabyte response boundary.

**Fix.** Follow LastEvaluatedKey until all pages are read and preserve consistent detail reads.

**Verification.** A test supplies incident metadata on page one and a timeline record on page two; it verifies the second request uses the continuation key and the returned detail includes the second-page event.

**Remaining.** Following database pages does not remove the synchronous API response-size limit. A very large timeline should move to an explicitly paginated timeline API/export path.

## 4. Lambda package layout and relative imports needed to agree

**Finding type: packaging review.** Python modules use package-relative imports. Zipping only their flat contents while configuring top-level handlers would break those imports.

**Fix.** Both Terraform's archive and the local package script preserve the backend/ directory. Handler paths are backend.api.handler, backend.processor.handler and backend.notifier.handler.

**Verification.** Package generation succeeded locally. The live ingestion/API smoke subsequently executed the deployed package and verified incident/outbox results and unauthenticated rejection. No packaging-related AWS runtime failure is claimed.

## 5. Compact Terraform blocks were not valid multiline HCL

**Observed failure.** The first formatting/init attempt rejected block declarations that started an argument on the opening line but continued other arguments on following lines. Examples included password_policy and nested configuration blocks.

**Cause and fix.** The generated source mixed single-line and multiline block syntax. Block boundaries were expanded, then terraform fmt normalized the files.

**Verification.** Initialization succeeded with aws 6.64.0, archive 2.8.0 and random 3.9.0; validate passed. DynamoDB hash_key/range_key deprecation warnings remained non-fatal. These are syntax/provider checks, not substitutes for an AWS plan or apply.

## 6. Windows sandbox ACLs hid installed SDK files and blocked esbuild

**Observed symptoms.** The Python suite initially passed twenty-six tests and failed four persistence tests with “No module named boto3.dynamodb.” The SDK appeared as a namespace without its normal module file. A direct directory read then showed access denied. The frontend build similarly reported denied ancestor-directory access while loading vite.config.ts.

**Diagnosis.** Downloaded dependencies existed, but the restricted process could not read their filesystem permissions. Installing another copy alone did not resolve the SDK symptom.

**Fix.** Execute the already-authorized local build/test with access to the installed dependencies. No application authentication was disabled, no AWS keys were embedded, and no user directory permissions were broadly loosened.

**Verification.** All thirty original Python tests passed with readable boto3. The frontend tests and production build passed. This was a local execution-environment issue, not an AWS service failure.

## 7. CLI login worked, but Python SDK login also needed CRT

**Observed integration dependency.** The integration lead verified the temporary AWS CLI profile and identified that its SDK login credential path required the AWS Common Runtime package.

**Fix.** The lead installed awscrt 0.36.3 into the shared local dependency directory. The smoke process used the verified temporary profile with readable boto3/CRT dependencies.

**Verification.** STS matched the expected account/non-root identity and the live backend smoke completed. No access keys, refresh tokens, credential files or personal email addresses are reproduced in the repository.

**Remaining.** A new machine must install the dependencies required by its chosen credential provider; a local profile name is not portable authentication.

## 8. Patching a test dependency exposed an npm resolver failure

**Observed findings.** The first frontend installation reported two moderate, development-only Vitest advisories. Updating to the patched 4.1.11 release hit “Cannot read properties of null (reading edgesOut)” during dependency resolution, including after rebuilding the disposable dependency directory.

**Fix.** Install the deliberate patched version using legacy peer resolution and record the same setting in .npmrc. This allowed a fresh lock/install to complete. The workaround did not bypass the tests, TypeScript build or security audit.

**Verification.** Vitest 4.1.11 ran all seven workflow tests successfully, Vite 7.3.6 built the SPA, and npm audit reported zero vulnerabilities. The deployment-waiter correction later expanded the Python suite to thirty-three passing tests.

**Remaining.** Dependencies still need periodic reviewed updates. legacy-peer-deps changes npm resolution behavior; it is documented rather than presented as a universal package-management recommendation.

## 9. Learning-account Lambda quotas differed from common defaults

**Observed constraint.** The integration lead read ten total concurrent Lambda executions and ten unreserved. The initial design reserved two per function, which would conflict with AWS's required unreserved pool on this small account.

**Fix.** Make lambda_reserved_concurrency configurable and default to -1, which uses the account pool. Keep the SQS mapping's maximum concurrency at two.

**Verification.** The revised plan and live application deployment completed; the bounded event-processing smoke passed. No quota increase, paid-plan upgrade or always-on compute was used as a workaround.

**Remaining.** Functions share the small account pool. API/notification bursts can contend; monitor throttles and queue age. Larger accounts can choose reserved capacity only after checking actual quotas.

## 10. First DynamoDB apply returned KMS NotFound

**Observed sequence.** The initial table creation returned a KMS key-not-found error. A subsequent read reported the relevant automatic key enabled. A reviewed retry then completed the application stack without reducing encryption.

**Interpretation.** The sequence is consistent with first-use propagation, but it does not prove that root cause. The journal does not label every KMS error “eventual consistency.”

**Verification and lesson.** Encryption remained configured, retry succeeded, and the later live transaction/outbox smoke passed. Check the exact service/key state and failed plan before retrying; do not disable encryption as a blanket fix.

## 11. CloudFront's default certificate ignored a stricter TLS minimum

**Observed behavior.** A refresh/plan showed a persistent difference between the requested TLSv1.2_2021 setting and AWS's stored TLSv1 setting for the default CloudFront certificate.

**Fix.** Record the actual TLSv1 value for that certificate. Document that the default hostname provides HTTPS but does not enforce a TLS 1.2 minimum. A stricter minimum needs a custom hostname/certificate and supported policy.

**Verification.** Terraform formatting/validation passed after the correction, and the integration lead replanned/applied the distribution. This avoids a perpetual configuration difference; it is not an assertion that the default endpoint rejects legacy TLS.

**Budget boundary.** No domain was purchased merely to improve a portfolio diagram. The production TLS/domain tradeoff remains explicit in [security](security.md).

## 12. First CodePipeline deployment stopped at a waiter permission mismatch

**Observed execution.** Source, Quality and Review succeeded. Deploy failed at 05:58:10 UTC while waiting for the first Lambda update. The exact CodeBuild error identified lambda:GetFunction denied on the project API function. The earlier update call had succeeded, but static asset uploads had not started; an empty-origin CloudFront 403 therefore did not indicate a frontend React failure.

**Cause.** FunctionUpdatedV2 uses GetFunction. The least-privilege deploy role allowed UpdateFunctionCode and GetFunctionConfiguration, matching the information needed to wait for an update.

**Fix.** Use FunctionUpdated, which polls GetFunctionConfiguration, with ninety two-second checks as a bound. Preserve the existing resource-scoped IAM rights instead of adding code-download metadata permission. The IaC comment records this coupling.

**Verification.** Three tests use the actual botocore waiter with stubbed responses: in-progress-to-success through configuration reads, stop before the next function on failure, and bounded timeout. The full thirty-three-test Python suite and Terraform format check passed.

**Release requirement.** A new source/build artifact must contain the correction; retrying the old Deploy artifact repeats its old script. The corrected live release and hosted-browser acceptance are recorded separately when the integration lead verifies them. See [CI/CD](ci-cd.md) and the [official waiter reference](https://docs.aws.amazon.com/boto3/latest/reference/services/lambda/waiter/FunctionUpdated.html).

## 13. A lasting public demo needs a different base path and data boundary

**New requirement.** Keep a usable preview available without leaving the AWS learning stack running.

**Implementation.** A separate Pages mode builds to dist-pages/ at /threatlens/. Configuration loading and the home link use Vite's base URL. The build helper overwrites the Pages artifact with demo mode and empty API/Cognito settings. The GitHub Pages workflow uses the official configure-pages, upload-pages-artifact and deploy-pages actions with the github-pages deployment environment.

**Separation.** AWS builds continue to use dist/ and the root path. Pages does not replace CodePipeline, authenticate against AWS or represent a live security feed. The environment URL will become a README preview link only after an actual Pages deployment is verified.

**Verification.** Seven frontend tests, the local Pages build/base/config checks, workflow YAML/environment checks and the separate AWS root-base build passed. Hosted Pages availability and its final URL are separate integration evidence.

## Current evidence boundary

Implemented and checked locally: detection/API/outbox logic, thirty-three Python tests, seven frontend tests, builds, dependency audit and Terraform validation. Verified live: the bounded AWS backend smoke with synthetic signals and API unauthenticated rejection. Actual local screenshots were captured, including a saved investigation note.

Do not infer completed hosted MFA sign-in, authenticated live note editing, successful corrected deployment, induced DLQ recovery, real SNS delivery, restore testing, Pages publication or teardown from code or this journal alone. The integration lead maintains those actual deployment outcomes. Real notifications remained disabled throughout this work.
