# Verified AWS teardown

The temporary ThreatLens AWS application was removed after its backend, pipeline and hosted-browser acceptance checks. Verification completed at **06:34:09 UTC on 11 September 2026**. The [permanent GitHub Pages demo](https://aliadiill.github.io/threatlens/) remains available with browser-only synthetic data.

## Executed sequence

1. Preserved the redacted backend/pipeline reports, authenticated browser screenshots and persisted-note evidence. Copied the existing Terraform state to a private evidence directory; credentials, real deployment variables and full state were not committed.
2. Prepared a saved destroy plan using the same application state and private deployment variable file. Reviewed all 75 managed resource deletions, with zero additions or changes. The two S3 buckets matched this project's names/tags. The shared CodeConnections connection and any separate state infrastructure were outside the plan.
3. Stopped the later documentation/Pages execution at its pending manual Review. Verified that neither project CodeBuild job was active. The previously successful application release remained recorded in [pipeline-result.json](pipeline-result.json).
4. Removed six versions/delete markers from the project pipeline bucket and four from the project frontend bucket. Both versioned buckets were verified empty; there were no incomplete multipart uploads. No other bucket was emptied.
5. Applied that exact saved plan. Terraform completed with **75 destroyed, zero added and zero changed**. The remaining managed-resource count in state was zero.
6. Queried the original resource identifiers independently through AWS service APIs. **Thirty-eight checks returned absence; one key check confirmed scheduled deletion.** Configuration children are additionally covered by their deleted parent resources and the empty Terraform state. The complete redacted result is [teardown-result.json](teardown-result.json).

## Verified result

| Resource group | Observed result |
| --- | --- |
| Three Lambda functions and two event-source mappings | Absent |
| HTTP API | Absent |
| CloudFront distribution, origin access control and response-header policy | Absent |
| Cognito analyst pool, including the temporary analyst | Pool absent |
| DynamoDB incident table | Absent |
| Two S3 buckets | Absent after version cleanup |
| Three SQS queues, SNS topic and dedicated EventBridge bus | Absent |
| CodePipeline and two CodeBuild projects | Absent |
| Five log groups, six alarms and six project IAM roles | Absent |
| Notification encryption key | PendingDeletion; AWS returned 18 September 2026 at 06:30:18 UTC |
| Automatically created DynamoDB SYSTEM backup | Retained by AWS; returned expiry 18 September 2026 at 06:30:18 UTC |

CloudFront took approximately three minutes twenty seconds to finish removal. The completion check used the service's absence response; it did not treat “disable requested” as deletion.

## Service-managed retention and cost boundary

The notification key is unusable for cryptographic operations while pending deletion. AWS documents no key-storage charge for a customer-managed key scheduled for deletion; canceling deletion would restore charges for that waiting period. The scheduled date is recorded from the actual service response, rather than claiming the key is already physically deleted. [AWS KMS pricing](https://aws.amazon.com/kms/pricing/), [KMS deletion behavior](https://docs.aws.amazon.com/kms/latest/developerguide/deleting-keys.html).

DynamoDB automatically created a SYSTEM backup because the deleted table had point-in-time recovery enabled. AWS documents this deletion backup at no additional cost. The API returned a seven-day expiry for this table; that observed timestamp is preserved in the evidence instead of assuming a generic maximum retention. No user-created or AWS Backup backup appeared in the table-scoped result. [DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/).

This verification covers the ThreatLens stack. It is not an account-wide billing reconciliation or a promise that earlier metered usage has already appeared in billing. The Free plan was preserved; no upgrade, real notification, paid domain or service subscription was introduced by teardown. Final portfolio-wide credit reconciliation belongs to the account-level evidence.

The repository, Pages deployment, documentation/screenshots, private state/history and shared CodeConnections resource were preserved. Recreating the live AWS application requires an intentional new reviewed deployment; the public demo does not recreate it.
