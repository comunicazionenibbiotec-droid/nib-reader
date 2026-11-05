# ZenPSA Playwright tests v0.1

## Scope
- Detector V2 experimental frontend and API contract.
- Reader V1 protected regression checks.
- No patient data, no database writes, no R2 uploads, no clinical interpretation.

## Install
Copy these files into the frontend/repository root. Then run:

```bash
npm install
npx playwright install chromium
npm run test:e2e
```

The default local server is:

```bash
python3 -m http.server 8080
```

Override configuration when needed:

```bash
ZENPSA_BASE_URL=https://your-frontend.example \
ZENPSA_USE_LOCAL_SERVER=0 \
npm run test:e2e
```

## Important assumptions
- The current public Detector V2 API is `https://nib-reader-api.onrender.com`.
- Frontend files are served from the repository root.
- Camera tests use a synthetic browser media stream, not a physical camera.
- The successful Detector V2 analysis UI test mocks the backend response. A separate health test checks the live Render endpoint.
- Reader V1 tests are deliberately non-destructive and do not perform a real patient capture.

## Commands
- `npm run test:e2e:v2`: Detector V2 only.
- `npm run test:e2e:v1`: Reader V1 only.
- `npm run test:e2e:mobile`: Pixel 7 viewport.
- `npm run test:e2e:headed`: visible browser.
- `npm run test:e2e:report`: open HTML report.

## Expected first adjustments
The Reader V1 page may require project-specific session/local-storage keys or navigation through `reader-clinical-data.html`. If the deployed version enforces that prerequisite, update only `prepareReader()` in `tests/e2e/reader-v1.spec.js`; do not weaken the isolation assertions.
