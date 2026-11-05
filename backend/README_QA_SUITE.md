# ZenPSA QA Agent + Playwright v0.2

This combined package installs the constrained ZenPSA QA Agent and non-destructive Playwright regression tests for Reader V1 and Detector V2.

## Main protections
- Reader V1 is fingerprinted through SHA-256 attachments in the test report.
- Detector V2 assets and routes must remain separate.
- Camera tests use a synthetic canvas stream.
- Detector V2 successful analysis is mocked for repeatability.
- The public Render health endpoint is checked independently.
- No patient records, PostgreSQL writes, R2 uploads or clinical calculations are performed.

## First command sequence

```bash
npm install
npx playwright install chromium
npm run test:e2e:v2 -- --project=desktop-chrome
npm run test:e2e:v1 -- --project=desktop-chrome
npm run test:e2e -- --project=mobile-chrome
```
