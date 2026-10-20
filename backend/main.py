import base64

import cv2
import numpy as np

from fastapi import FastAPI

from fastapi.middleware.cors import (
    CORSMiddleware
)

from models import ImageRequest

from detector import detect_device

from alignment import alignment_score

from image_quality import (
    evaluate_quality
)

from analytical_reader import (
    analyze_windows
)


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/")
def root():
    return {
        "status": "online",
        "version": "analytical-reading-1.0"
    }


@app.post("/analyze")
def analyze(data: ImageRequest):
    try:
        image_string = data.image

        if "," in image_string:
            image_string = (
                image_string
                .split(",", 1)[1]
            )

        image_bytes = base64.b64decode(
            image_string
        )

        image_array = np.frombuffer(
            image_bytes,
            np.uint8
        )

        image = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        if image is None:
            return {
                "accepted": False,
                "error": "image_decode_error"
            }

        quality = evaluate_quality(
            image
        )

        detection = detect_device(
            image
        )

        if detection is None:
            return {
                "accepted": False,
                "test_detected": False,
                "reason": "device_not_found",
                "quality": quality,
                "image_width": int(
                    image.shape[1]
                ),
                "image_height": int(
                    image.shape[0]
                )
            }

        bbox = detection["bbox"]

        score = alignment_score(
            bbox["w"],
            bbox["h"]
        )

        windows = detection["windows"]

        geometry_ok = detection[
            "geometry_ok"
        ]

        analytical_results = {
            "A": {
                "analysis_ok": False,
                "reason": "geometry_not_valid"
            },
            "C": {
                "analysis_ok": False,
                "reason": "geometry_not_valid"
            }
        }

        if geometry_ok:
            analytical_results = (
                analyze_windows(
                    detection[
                        "normalized_image"
                    ],
                    windows
                )
            )

        analysis_a_ok = (
            analytical_results
            .get("A", {})
            .get("analysis_ok", False)
        )

        analysis_c_ok = (
            analytical_results
            .get("C", {})
            .get("analysis_ok", False)
        )

        analytical_reading_ok = (
            analysis_a_ok and
            analysis_c_ok
        )

        accepted = (
            quality["accepted"] and
            geometry_ok and
            analytical_reading_ok
        )

        reasons = list(
            quality["reasons"]
        )

        if not geometry_ok:
            reasons.append(
                "window_geometry_not_valid"
            )

        if not analysis_a_ok:
            reasons.append(
                "window_A_analysis_failed"
            )

        if not analysis_c_ok:
            reasons.append(
                "window_C_analysis_failed"
            )

        test_state = determine_test_state(
            analytical_results
        )

        next_step = determine_next_step(
            accepted,
            test_state
        )

        return {
            "accepted": accepted,

            "test_detected": True,

            "quality": quality,

            "alignment_score": score,

            "bbox": bbox,

            "device_metrics": detection[
                "device_metrics"
            ],

            "normalized_device": detection[
                "normalized_size"
            ],

            "windows": windows,

            "window_A_detected": (
                windows["A"]["detected"]
            ),

            "window_C_detected": (
                windows["C"]["detected"]
            ),

            "geometry_ok": geometry_ok,

            "analytical_reading": {
                "ok":
                    analytical_reading_ok,

                "A":
                    analytical_results["A"],

                "C":
                    analytical_results["C"]
            },

            "test_state": test_state,

            "reasons": reasons,

            "image_width": int(
                image.shape[1]
            ),

            "image_height": int(
                image.shape[0]
            ),

            "next_step": next_step
        }

    except Exception as error:
        return {
            "accepted": False,
            "error": str(error)
        }


def determine_test_state(
    analytical_results
):
    result_a = analytical_results.get(
        "A",
        {}
    )

    result_c = analytical_results.get(
        "C",
        {}
    )

    if (
        not result_a.get(
            "analysis_ok",
            False
        ) or
        not result_c.get(
            "analysis_ok",
            False
        )
    ):
        return "analysis_failed"

    color_state = result_a.get(
        "color_state",
        "unknown"
    )

    line_count = result_c.get(
        "line_count",
        0
    )

    if (
        color_state ==
        "blank_or_unreacted" and
        line_count == 0
    ):
        return "not_run"

    if line_count == 0:
        return "invalid_no_control_line"

    if line_count == 1:
        return "valid_one_line"

    if line_count >= 2:
        return "valid_two_lines"

    return "unknown"


def determine_next_step(
    accepted,
    test_state
):
    if not accepted:
        return "repeat_or_review"

    if test_state == "not_run":
        return "test_not_run"

    if test_state == (
        "invalid_no_control_line"
    ):
        return "repeat_test"

    if test_state in [
        "valid_one_line",
        "valid_two_lines"
    ]:
        return (
            "semiquantitative_calibration"
        )

    return "manual_review"