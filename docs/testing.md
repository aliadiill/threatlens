# Test evidence

Local implementation checks were run on 11 September 2026 UTC.

| Check | Result |
| --- | --- |
| Python behavioral suite | 33 tests passed after the deployment waiter correction: 30 application tests plus 3 actual-SDK waiter regression tests |
| React/TypeScript workflow suite | Seven tests passed on Vitest 4.1.11; final run 05:37 UTC |
| TypeScript + Vite production build | Passed on Vite 7.3.6; 32 modules, final drawer-error-display build 245.12 kB JS and 11.27 kB CSS before gzip |
| Terraform init | Passed with aws 6.64.0, archive 2.8.0, random 3.9.0 |
| Terraform validate | Passed; provider warns about deprecated DynamoDB hash_key/range_key syntax |
| Source security guardrail | Passed across backend, TypeScript and Terraform source files |
| npm dependency audit | Zero vulnerabilities after updating Vitest to 4.1.11 |
| GitHub Pages local artifact | Passed: seven frontend tests, pages-mode build, explicit demo-only configuration, /threatlens/ assets/config/home base, valid workflow/environment; separate standard AWS build also passed |
| GitHub Pages hosted deployment | Not established by local artifact checks; add the permanent link only after the integration lead verifies the actual deployment URL |
| AWS infrastructure | Integration lead completed the application stack; initial DynamoDB creation was retried without changing encryption settings |
| Live AWS backend smoke | PASS, 05:56:08–05:56:26 UTC: 15 safe custom-event submissions, ten expected incidents and ten SIMULATED outboxes, replay preserved identities/versions, observed queue/DLQ counts zero, unauthenticated API 401 |
| Hosted sign-in/authenticated browser edits, real SNS delivery, induced DLQ recovery, full pipeline execution, restore | Not established by the backend smoke; integration task must add independent actual evidence |
| Screenshots | Integration lead captured the actual local demo overview and investigation; saved note was confirmed in the rendered timeline. Files are in docs/screenshots and are labeled as synthetic local data |

The Python suite checks twelve signals producing ten findings; five rule categories; severity mapping; successful versus failed privileged changes; benign HTTPS versus public SSH; IPv6; event identity/time validation; bounded generator; duplicate processing; per-record failures; storage retries; access-token requirements; mass-assignment rejection; resolution notes; optimistic conflicts; atomic transaction shape; duplicate versus other transaction failure; pagination; and notification failures.

Notification tests intentionally demonstrate two publishes when the SENT marker fails after a successful publish. This is expected at-least-once behavior, not a test failure.

Initial local attempts exposed Windows filesystem restrictions that made downloaded SDK files appear as an empty namespace and blocked esbuild's ancestor-directory reads. Re-running with authorized access fixed the environment; the application did not bypass its AWS authentication. An npm peer-resolution error required the recorded legacy-peer-deps setting; the final lock and tests are the reproducible artifacts.

## Reproduce

```sh
npm ci
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
npm test
npm run build
npm audit --audit-level=high
python scripts/check_security.py
terraform -chdir=infra init -backend=false
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
```

These are offline/unit/build checks except dependency downloads/advisory queries. Fake clients verify application behavior; they do not establish AWS policy correctness or service integration. The deployment guide contains the live acceptance checklist.

## Actual live backend result

The separately authorized AWS smoke run used the deployed EventBridge → SQS → Lambda → DynamoDB → stream-notifier path. [live-smoke-result.json](live-smoke-result.json) is the redacted runtime output, and [live-smoke.md](live-smoke.md) describes the bounded procedure. The test read only the twenty expected incident/outbox keys; it did not scan the entire account or table. Its queue counts are approximate service attributes.

No real notification was requested or sent by this test; the Lambda environment was checked for disabled notification delivery before publishing. No Cognito user was created/changed. The source of all fifteen submissions was threatlens.demo. These are actual AWS integration results for synthetic events, not evidence of real cloud attacks or a production security audit.
