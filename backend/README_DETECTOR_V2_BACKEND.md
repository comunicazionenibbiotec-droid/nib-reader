# Detector V2 backend v0.1

Experimental, isolated OpenCV pipeline for cassette geometry. It does not change `/analyze`, clinical results, calibration, PostgreSQL, R2, uPSA or uZinc.

## Files
- `detector_v2.py`: quadrilateral candidates, 4-corner ordering, perspective correction to 1200x2400, expected A/B/C regions and experimental geometry scores.
- `regional_quality_v2.py`: focus, brightness percentiles, glare and valid-pixel metrics by region.
- `detector_v2_router.py`: `/detector-v2/health` and `/detector-v2/analyze` endpoints with no persistence.
- `main.py`: current main with only the new router import and include.

## Install
1. Back up the deployed backend.
2. Copy the three new modules to the backend root.
3. Compare and then replace `main.py`; its only intended differences are the Detector V2 router import/include.
4. Deploy to staging first.
5. Test `GET /detector-v2/health`.

## Current limitation
The detector is intentionally preliminary and has only a synthetic smoke test. Real thresholds, expected A/B/C coordinates and geometry scoring must be tuned using real captures. Do not use its output for patient samples or clinical decisions.

## v0.2
Canonical crop changed from 1200x2400 to 1200x2340 to match the current cassette template aspect ratio (~1.95) instead of stretching every detected quadrilateral to 2.00. The response now reports source quadrilateral width/height/aspect and a diagnostic vertical_stretch_ratio.

## v0.3
Fix for visibly tilted/stretched canonical previews. V2 now rejects implausible cassette aspect ratios (outside 1.55-2.35), prefers real 4-corner contours when available, and preserves the aspect ratio of the detected quadrilateral during perspective rectification instead of forcing every candidate into a fixed 1200x2340 rectangle. The nominal template height remains reported for comparison only.
