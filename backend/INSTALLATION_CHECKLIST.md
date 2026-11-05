# Installation checklist

1. Confirm this is the latest working ZenPSA-pro repository.
2. Create branch `chore/qa-agent-playwright-baseline`.
3. Copy this package to the repository root.
4. Merge `.gitignore.zenpsa-qa` entries into the project `.gitignore`.
5. Run `npm install` and commit generated `package-lock.json`.
6. Run `npx playwright install chromium`.
7. Run `npm run test:e2e:v2 -- --project=desktop-chrome`.
8. Run `npm run test:e2e:v1 -- --project=desktop-chrome`.
9. Run `npm run test:e2e -- --project=mobile-chrome`.
10. Review the HTML report before opening the pull request.

Do not deploy from this branch. Do not place real patient images in `tests/fixtures`.
