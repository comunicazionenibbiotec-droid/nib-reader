# ZenPSA-pro AI Agent Policy

## Current operating mode
The only authorized agent is **ZenPSA QA Agent**. It is read-only by default.

The agent may:
- inspect source code and dependency relationships;
- run static checks and automated tests;
- analyze logs and synthetic/de-identified R&D images;
- produce defect reports and proposed patches;
- create changes only in a separate branch or pull request when explicitly requested.

The agent must not:
- deploy or merge;
- change production data or run destructive migrations;
- access identifiable patient data;
- change clinical cut-offs, risk matrices, calibration models or diagnostic wording;
- modify Reader V1, ROI Editor, crop, zoom, autofocus, uPSA, uZinc, QMS, PostgreSQL or R2 unless the exact task explicitly authorizes the file and the latest working version has been confirmed.

## Mandatory baseline rule
Before any code modification, establish that the workspace contains the latest working frontend and backend. If this cannot be established, stop and request the latest working files from Sergio Occhipinti.

## Protected production path
The following remain the production baseline until explicitly replaced:
- `index.html` and Reader V1 frontend modules;
- backend `/analyze` and `detector.py`;
- uPSA analysis and concordance;
- current uZinc exploratory analysis;
- ROI Editor;
- PostgreSQL records and Cloudflare R2 storage.

Detector V2 is experimental and isolated:
- frontend: `detector-v2.html` and `detectorV2*.js`;
- backend: `/detector-v2/*`, `detector_v2.py`, `detector_v2_router.py`, `regional_quality_v2.py`.

## Required response for every audit
1. Scope and baseline
2. Files inspected
3. Tests run
4. Findings with severity: blocker, high, medium, low
5. Reproduction steps
6. Evidence
7. Smallest proposed fix
8. Regression risk
9. Rollback method
10. Items requiring Sergio's decision
