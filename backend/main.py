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
        "version": "roi-detection-1.0"
    }


@app.post("/analyze")
def analyze(data: ImageRequest):
    try:
        image_string = (
            data.image
        )

        if "," in image_string:
            image_string = (
                image_string
                .split(",", 1)[1]
            )

        image_bytes = (
            base64.b64decode(
                image_string
            )
        )

        image_array = (
            np.frombuffer(
                image_bytes,
                np.uint8
            )
        )

        image = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        if image is None:
            return {
                "accepted": False,
                "error":
                    "image_decode_error"
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
                "reason":
                    "device_not_found",
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

        geometry_ok = detection[
            "geometry_ok"
        ]

        windows = detection[
            "windows"
        ]

        accepted = (
            quality["accepted"] and
            geometry_ok
        )

        reasons = list(
            quality["reasons"]
        )

        if not geometry_ok:
            reasons.append(
                "window_geometry_not_valid"
            )

        next_step = (
            "analytical_reading"
            if accepted
            else "repeat_or_review"
        )

        return {
            "accepted": accepted,

            "test_detected": True,

            "quality": quality,

            "alignment_score":
                score,

            "bbox": bbox,

            "device_metrics":
                detection[
                    "device_metrics"
                ],

            "normalized_device": (
                detection[
                    "normalized_size"
                ]
            ),

            "windows": windows,

            "window_A_detected": (
                windows["A"][
                    "detected"
                ]
            ),

            "window_C_detected": (
                windows["C"][
                    "detected"
                ]
            ),

            "geometry_ok":
                geometry_ok,

            "reasons":
                reasons,

            "image_width": int(
                image.shape[1]
            ),

            "image_height": int(
                image.shape[0]
            ),

            "next_step":
                next_step
        }

    except Exception as error:
        return {
            "accepted": False,
            "error": str(error)
        }