# Bounded AWS smoke test

`scripts/live_smoke.py` is the reproducible live-backend check. It is separate from the offline suite and must run only against the reviewed ThreatLens deployment using temporary credentials.

The script verifies the expected account and non-root identity; checks the project resource names/queue ownership; confirms the notifier is configured for simulation; verifies unauthenticated API rejection; then submits twelve safe custom events and three suspicious-event replays. A hard per-run cap prevents more than fifteen submitted events, including partially failed submissions. Do not restart a failed publishing run casually; first inspect its recorded submission count and the failure.

The live smoke uses the current UTC time for its synthetic events. The source remains `threatlens.demo`, so these events are never labeled as real suspicious AWS operations. It calls no destructive AWS APIs, never changes Cognito users, and never calls SNS or email.

Expected outcome: ten known incident records, ten outbox records marked SIMULATED, unchanged incident identities/versions after replay, no input backlog, and no DLQ messages. Queue counts are approximate AWS attributes, not a transactional guarantee. The known-key database checks use consistent reads. The API check is unauthenticated only; hosted sign-in and authenticated note/status persistence are independent browser acceptance checks.

```sh
terraform -chdir=infra output -json > build/live-outputs.json
python scripts/live_smoke.py --outputs build/live-outputs.json --expected-account YOUR_ACCOUNT_ID --profile YOUR_TEMPORARY_PROFILE
```

Keep the output file under ignored build storage. The resulting `docs/live-smoke-result.json` intentionally omits account IDs, ARNs, queue URLs, recipient information and raw event parameters. A missing result file means the test has not been run; PASS must be supported by the actual runtime checks, not this procedure.

The notifier's environment configuration is read only to guard against accidental real sends. If notifications are enabled, the script stops before publishing. The DynamoDB/queue and API checks operate only on resources from the supplied project outputs. They do not inventory or change unrelated resources.

## Executed result

The run on 11 September 2026, 05:56:08–05:56:26 UTC, **passed**. It submitted exactly fifteen safe events: twelve initial samples and three replays. All ten expected incident keys and ten corresponding SIMULATED outboxes appeared. Replay left those incident IDs and versions unchanged. The observed input and DLQ visible/in-flight counts were zero, and the unauthenticated API returned 401. No live event quota beyond the fifteen submissions was used by this test.

The machine-readable [runtime report](live-smoke-result.json) contains these actual results. Hosted user login, authenticated note updates, induced failure/redrive, real notification delivery and restore remain separate acceptance tests.
