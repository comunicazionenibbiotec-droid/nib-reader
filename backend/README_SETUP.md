# ZenPSA QA Agent v0.1

## Objective
Introduce one constrained AI agent for quality assurance and development support. The agent is not part of the clinical application and is not authorized to make clinical decisions.

## Installation
Copy `AGENTS.md`, `.github`, and `tests` into the root of the latest working ZenPSA-pro repository. Use a dedicated branch such as `chore/qa-agent-baseline`.

## First run
1. Confirm the repository is the latest working frontend/backend.
2. Protect `main` and require pull-request review.
3. Select **ZenPSA QA Agent**.
4. Run `audit-detector-v2.prompt.md` in read-only mode.
5. Do not authorize code changes during the first run.

## Expected first deliverable
- repository and dependency map;
- Reader V1 protected-file inventory;
- Detector V2 frontend/backend contract check;
- list of missing test prerequisites;
- prioritized defects;
- no production code changes.

## Recommended next additions
- configure `pytest` TestClient for FastAPI;
- install Playwright in the existing frontend toolchain;
- add synthetic cassette images;
- add de-identified R&D image fixtures only when available;
- add baseline screenshots for 375, 390, 412 and 430 px widths.
