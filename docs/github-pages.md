# GitHub Pages demonstration

The Pages deployment is a browser-only preview that can remain available after billable AWS demonstration resources are removed. It complements the requested GitHub → AWS CodePipeline → CodeBuild workflow; it does not replace the live system.

## Build and data boundary

Run:

```sh
npm ci
npm test
npm run build:pages
```

Vite's pages mode sets base=/threatlens/ and writes dist-pages/. The standard npm run build still writes dist/ with the root base for CloudFront. Keeping directories separate prevents a Pages build from overwriting an AWS deployment artifact.

The preparation script explicitly writes a demo configuration with empty API URL, Cognito domain, client ID and scopes. The app fetches configuration relative to import.meta.env.BASE_URL, and its brand/home link uses the same base. Hash links stay inside the project site.

The preview shows fixed synthetic sample data and a visible demo banner. Investigation edits persist in the visitor's browser localStorage only. It does not call AWS APIs, send notifications or prompt for Cognito credentials. Reset demo restores the deterministic fixture.

Local verification on 11 September 2026 passed: seven frontend tests; the Pages build and its artifact checks; YAML parsing and github-pages environment check; and a subsequent standard AWS build. The Pages index references /threatlens/assets/ while the separate AWS index retains /assets/.

The integration lead subsequently verified the hosted [permanent demo](https://aliadiill.github.io/threatlens/) from [workflow run 34569307423](https://github.com/aliadiill/threatlens/actions/runs/34569307423), saved its screenshot and configured About/topics/website/Deployments metadata. See the [actual browser record](live-browser.md).

## Workflow

.github/workflows/pages-demo.yml runs on main pushes or manual dispatch. It installs the lock, runs the analyst tests, builds/validates the demo artifact, audits dependencies, and uploads only dist-pages/. A separate deploy job publishes through the github-pages environment, whose URL comes from the deployment action output.

The workflow uses GitHub's official [configure-pages](https://github.com/actions/configure-pages), [upload-pages-artifact](https://github.com/actions/upload-pages-artifact) and [deploy-pages](https://github.com/actions/deploy-pages) actions. It does not store AWS credentials or grant AWS access.

The repository administrator must enable GitHub Pages with GitHub Actions as its source and configure the deployment environment. Root/lead task owns that setting and the GitHub About/topics/website metadata. No personal paid GitHub plan or custom domain is required by this code; account eligibility and actual hosting availability must be checked before publication.

## Verification before adding a permanent link

1. Confirm the Pages build and deployment jobs succeeded for the intended commit.
2. Open the returned deployment URL and verify it uses the project path.
3. Confirm config.json is demo mode with empty live connection settings.
4. Verify no asset/config 404s, incident filtering, an investigation note/status update, reload persistence and the home link.
5. Confirm the UI still labels the sample data and browser-local behavior.
6. Add the verified deployment URL to README and repository website metadata. Do not guess the URL from the account name or treat a workflow file as proof of publication.
