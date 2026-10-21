import base64

import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import ImageRequest
from detector import detect_device
from alignment import alignment_score
from image_quality import evaluate_quality
from analytical_reader import analyze_windows
from calibration_manager import CalibrationError, get_default_lot_id
from database import create_database_tables
from records_router import router as records_router


app = FastAPI()

app.include_router(records_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(
        "ZENPSA: database startup beginning",
        flush=True,
    )

    create_database_tables()

    print(
        "ZENPSA: database startup completed",
        flush=True,
    )

    yield

@app.get("/")
def root():
    return {
        "status": "online",
        "version": "analytical-reading-1.2.1",
    }


@app.post("/analyze")
def analyze(data: ImageRequest):
    try:
        image = decode_image(data.image)

        if image is None:
            return {
                "accepted": False,
                "error": "image_decode_error",
                "next_step": "repeat_or_review",
            }

        image_height, image_width = image.shape[:2]
        quality = evaluate_quality(image)
        detection = detect_device(image)

        if detection is None:
            return {
                "accepted": False,
                "test_detected": False,
                "reason": "device_not_found",
                "quality": quality,
                "image_width": int(image_width),
                "image_height": int(image_height),
                "next_step": "repeat_or_review",
            }

        bbox = detection["bbox"]
        score = alignment_score(bbox["w"], bbox["h"])
        windows = detection.get("windows", {})
        geometry_ok = bool(detection.get("geometry_ok", False))
        lot_id = resolve_lot_id(data)

        analytical_results = create_empty_analytical_results(
            "geometry_not_valid"
        )

        if geometry_ok:
            analytical_results = analyze_windows(
                detection["normalized_image"],
                windows,
                lot_id,
            )

        analysis_a = analytical_results.get("A", {})
        analysis_c = analytical_results.get("C", {})
        analysis_a_ok = bool(analysis_a.get("analysis_ok", False))
        analysis_c_ok = bool(analysis_c.get("analysis_ok", False))
        analytical_reading_ok = analysis_a_ok and analysis_c_ok

        test_state = determine_test_state(analytical_results)
        test_valid = determine_test_validity(test_state, analytical_results)

        reasons = collect_reasons(
            quality,
            geometry_ok,
            analysis_a_ok,
            analysis_c_ok,
            test_state,
        )

        accepted = determine_accepted(
            quality,
            geometry_ok,
            analytical_reading_ok,
            test_state,
        )

        next_step = determine_next_step(test_state, accepted)

        return {
            "accepted": accepted,
            "test_detected": True,
            "quality": quality,
            "alignment_score": score,
            "bbox": bbox,
            "device_metrics": detection.get("device_metrics", {}),
            "normalized_device": detection.get("normalized_size", {}),
            "windows": windows,
            "window_A_detected": bool(
                windows.get("A", {}).get("detected", False)
            ),
            "window_C_detected": bool(
                windows.get("C", {}).get("detected", False)
            ),
            "geometry_ok": geometry_ok,
            "analytical_reading": {
                "ok": analytical_reading_ok,
                "lot_id": lot_id,
                "A": analysis_a,
                "C": analysis_c,
            },
            "test_valid": test_valid,
            "test_state": test_state,
            "reasons": reasons,
            "image_width": int(image_width),
            "image_height": int(image_height),
            "next_step": next_step,
        }

    except CalibrationError as error:
        return {
            "accepted": False,
            "error": str(error),
            "reason": "calibration_configuration_error",
            "next_step": "review_lot_configuration",
        }

    except Exception as error:
        return {
            "accepted": False,
            "error": str(error),
            "reason": "unexpected_backend_error",
            "next_step": "technical_review",
        }


def decode_image(image_string):
    if not image_string:
        return None

    if "," in image_string:
        image_string = image_string.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(image_string, validate=True)
    except Exception:
        return None

    image_array = np.frombuffer(image_bytes, np.uint8)
    return cv2.imdecode(image_array, cv2.IMREAD_COLOR)


def resolve_lot_id(data):
    metadata = getattr(data, "metadata", None)

    if isinstance(metadata, dict):
        metadata_lot_id = metadata.get("lot_id")
        if metadata_lot_id:
            return str(metadata_lot_id)

    direct_lot_id = getattr(data, "lot_id", None)
    if direct_lot_id:
        return str(direct_lot_id)

    return get_default_lot_id()


def create_empty_analytical_results(reason):
    return {
        "A": {"analysis_ok": False, "reason": reason},
        "C": {"analysis_ok": False, "reason": reason},
    }


def determine_test_state(analytical_results):
    result_a = analytical_results.get("A", {})
    result_c = analytical_results.get("C", {})

    if not result_a.get("analysis_ok", False):
        return "analysis_failed"

    if not result_c.get("analysis_ok", False):
        return "analysis_failed"

    color_state = result_a.get("color_state", "unknown")
    control_present = bool(result_c.get("control_line_present", False))
    test_present = bool(result_c.get("test_line_present", False))
    distance_valid = result_c.get("distance_valid")
    c_state = result_c.get("test_state", "unknown")

    if (
        color_state == "blank_or_unreacted"
        and not control_present
        and not test_present
    ):
        return "not_run"

    if c_state == "invalid_line_spacing":
        return "invalid_line_spacing"

    if test_present and not control_present:
        return "invalid_missing_control_line"

    if not control_present:
        return "invalid_no_control_line"

    if control_present and not test_present:
        return "valid_one_line"

    if control_present and test_present:
        if distance_valid is False:
            return "invalid_line_spacing"
        return "valid_two_lines"

    return "unknown"


def determine_test_validity(test_state, analytical_results):
    result_c = analytical_results.get("C", {})
    c_valid = bool(result_c.get("test_valid", False))
    return c_valid and test_state in {"valid_one_line", "valid_two_lines"}


def determine_accepted(
    quality,
    geometry_ok,
    analytical_reading_ok,
    test_state,
):
    if not quality.get("accepted", False):
        return False

    if not geometry_ok or not analytical_reading_ok:
        return False

    if test_state == "not_run":
        return True

    return test_state in {"valid_one_line", "valid_two_lines"}


def collect_reasons(
    quality,
    geometry_ok,
    analysis_a_ok,
    analysis_c_ok,
    test_state,
):
    reasons = list(quality.get("reasons", []))

    if not geometry_ok:
        reasons.append("window_geometry_not_valid")

    if not analysis_a_ok:
        reasons.append("window_A_analysis_failed")

    if not analysis_c_ok:
        reasons.append("window_C_analysis_failed")

    state_reasons = {
        "analysis_failed": "analytical_reading_failed",
        "invalid_missing_control_line": "control_line_missing",
        "invalid_no_control_line": "control_line_missing",
        "invalid_line_spacing": "line_spacing_not_compatible_with_lot",
        "unknown": "test_state_unknown",
    }

    state_reason = state_reasons.get(test_state)
    if state_reason and state_reason not in reasons:
        reasons.append(state_reason)

    return reasons


def determine_next_step(test_state, accepted):
    if test_state == "not_run":
        return "test_not_run"

    if test_state in {
        "invalid_missing_control_line",
        "invalid_no_control_line",
    }:
        return "repeat_test"

    if test_state == "invalid_line_spacing":
        return "review_lot_or_repeat_test"

    if test_state == "analysis_failed":
        return "repeat_or_review"

    if not accepted:
        return "repeat_or_review"

    if test_state in {"valid_one_line", "valid_two_lines"}:
        return "semiquantitative_calibration"

    return "manual_review"
