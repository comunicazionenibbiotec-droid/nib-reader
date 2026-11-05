Follow `AGENTS.md` as the authoritative project policy.

ZenPSA-pro is a MedTech platform. Prefer deterministic, testable behavior. AI may assist development and R&D analysis but must not generate or alter clinical conclusions.

For code analysis:
- preserve existing filenames, IDs, routes and API payloads;
- do not refactor unrelated code;
- separate Reader V1 from Detector V2;
- use synthetic or de-identified fixtures only;
- never commit secrets, `.env`, database URLs, R2 credentials or tokens;
- report uncertainty instead of inventing missing behavior.

For Detector V2, verify:
- camera and permissions;
- torch state;
- focus, brightness and stability metrics;
- glare in windows A, B and C;
- cassette quadrilateral detection;
- perspective correction;
- source aspect ratio and stretch ratio;
- A/B/C geometry;
- API health and analyze responses;
- no persistence and no clinical use.
