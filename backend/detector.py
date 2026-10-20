import cv2
import numpy as np


NORMALIZED_WIDTH = 800
NORMALIZED_HEIGHT = 1600


DEVICE_MIN_ASPECT_RATIO = 1.75
DEVICE_MAX_ASPECT_RATIO = 2.25

DEVICE_MIN_AREA_RATIO = 0.03
DEVICE_MAX_AREA_RATIO = 0.35


WINDOW_A_RELATIVE = {
    "x1": 0.16,
    "y1": 0.11,
    "x2": 0.45,
    "y2": 0.31
}


WINDOW_C_RELATIVE = {
    "x1": 0.56,
    "y1": 0.38,
    "x2": 0.82,
    "y2": 0.69
}


def detect_device(image):
    if image is None:
        return None

    image_height, image_width = (
        image.shape[:2]
    )

    image_area = (
        image_width *
        image_height
    )

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    blurred = cv2.GaussianBlur(
        gray,
        (7, 7),
        0
    )

    _, threshold = cv2.threshold(
        blurred,
        180,
        255,
        cv2.THRESH_BINARY
    )

    contours, _ = cv2.findContours(
        threshold,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = []

    for contour in contours:
        contour_area = cv2.contourArea(
            contour
        )

        if contour_area <= 0:
            continue

        x, y, width, height = (
            cv2.boundingRect(
                contour
            )
        )

        if width <= 0 or height <= 0:
            continue

        aspect_ratio = (
            height /
            width
        )

        area_ratio = (
            contour_area /
            image_area
        )

        if (
            aspect_ratio <
            DEVICE_MIN_ASPECT_RATIO
        ):
            continue

        if (
            aspect_ratio >
            DEVICE_MAX_ASPECT_RATIO
        ):
            continue

        if (
            area_ratio <
            DEVICE_MIN_AREA_RATIO
        ):
            continue

        if (
            area_ratio >
            DEVICE_MAX_AREA_RATIO
        ):
            continue

        center_x = (
            x +
            width / 2
        )

        center_y = (
            y +
            height / 2
        )

        image_center_x = (
            image_width / 2
        )

        image_center_y = (
            image_height / 2
        )

        center_distance = np.sqrt(
            (
                center_x -
                image_center_x
            ) ** 2 +
            (
                center_y -
                image_center_y
            ) ** 2
        )

        image_diagonal = np.sqrt(
            image_width ** 2 +
            image_height ** 2
        )

        normalized_center_distance = (
            center_distance /
            image_diagonal
        )

        expected_aspect_ratio = 2.02

        aspect_error = abs(
            aspect_ratio -
            expected_aspect_ratio
        )

        aspect_score = max(
            0.0,
            1.0 -
            aspect_error / 0.5
        )

        center_score = max(
            0.0,
            1.0 -
            normalized_center_distance * 4
        )

        rectangular_area = (
            width *
            height
        )

        fill_ratio = (
            contour_area /
            rectangular_area
        )

        candidate_score = (
            0.45 *
            aspect_score +
            0.30 *
            center_score +
            0.25 *
            fill_ratio
        )

        candidates.append({
            "contour": contour,
            "score": float(
                candidate_score
            ),
            "x": int(x),
            "y": int(y),
            "w": int(width),
            "h": int(height),
            "aspect_ratio": float(
                aspect_ratio
            ),
            "area_ratio": float(
                area_ratio
            ),
            "fill_ratio": float(
                fill_ratio
            )
        })

    if not candidates:
        return None

    candidates.sort(
        key=lambda candidate:
            candidate["score"],
        reverse=True
    )

    best_candidate = (
        candidates[0]
    )

    x = best_candidate["x"]
    y = best_candidate["y"]
    width = best_candidate["w"]
    height = best_candidate["h"]

    device_image = image[
        y:y + height,
        x:x + width
    ]

    if device_image.size == 0:
        return None

    normalized_device = cv2.resize(
        device_image,
        (
            NORMALIZED_WIDTH,
            NORMALIZED_HEIGHT
        ),
        interpolation=cv2.INTER_CUBIC
    )

    window_a = extract_window(
        normalized_device,
        WINDOW_A_RELATIVE,
        "A"
    )

    window_c = extract_window(
        normalized_device,
        WINDOW_C_RELATIVE,
        "C"
    )

    geometry_ok = (
        window_a["detected"] and
        window_c["detected"]
    )

    return {
        "image": device_image,
        "normalized_image":
            normalized_device,

        "bbox": {
            "x": x,
            "y": y,
            "w": width,
            "h": height
        },

        "device_metrics": {
            "candidate_score": round(
                best_candidate["score"],
                3
            ),
            "aspect_ratio": round(
                best_candidate[
                    "aspect_ratio"
                ],
                3
            ),
            "area_ratio": round(
                best_candidate[
                    "area_ratio"
                ],
                4
            ),
            "fill_ratio": round(
                best_candidate[
                    "fill_ratio"
                ],
                3
            ),
            "candidate_count": len(
                candidates
            )
        },

        "normalized_size": {
            "width":
                NORMALIZED_WIDTH,
            "height":
                NORMALIZED_HEIGHT
        },

        "windows": {
            "A": window_a,
            "C": window_c
        },

        "geometry_ok":
            geometry_ok
    }


def extract_window(
    normalized_device,
    relative_coordinates,
    window_name
):
    x1 = int(
        round(
            relative_coordinates[
                "x1"
            ] *
            NORMALIZED_WIDTH
        )
    )

    y1 = int(
        round(
            relative_coordinates[
                "y1"
            ] *
            NORMALIZED_HEIGHT
        )
    )

    x2 = int(
        round(
            relative_coordinates[
                "x2"
            ] *
            NORMALIZED_WIDTH
        )
    )

    y2 = int(
        round(
            relative_coordinates[
                "y2"
            ] *
            NORMALIZED_HEIGHT
        )
    )

    x1 = max(
        0,
        min(
            x1,
            NORMALIZED_WIDTH - 1
        )
    )

    y1 = max(
        0,
        min(
            y1,
            NORMALIZED_HEIGHT - 1
        )
    )

    x2 = max(
        x1 + 1,
        min(
            x2,
            NORMALIZED_WIDTH
        )
    )

    y2 = max(
        y1 + 1,
        min(
            y2,
            NORMALIZED_HEIGHT
        )
    )

    roi = normalized_device[
        y1:y2,
        x1:x2
    ]

    detected = (
        roi is not None and
        roi.size > 0 and
        roi.shape[0] >= 50 and
        roi.shape[1] >= 50
    )

    if not detected:
        return {
            "detected": False,
            "name": window_name,
            "reason":
                "invalid_roi"
        }

    metrics = evaluate_roi(
        roi
    )

    return {
        "detected": True,
        "name": window_name,

        "bbox_normalized": {
            "x": x1,
            "y": y1,
            "w": x2 - x1,
            "h": y2 - y1
        },

        "bbox_relative": {
            "x1":
                relative_coordinates[
                    "x1"
                ],
            "y1":
                relative_coordinates[
                    "y1"
                ],
            "x2":
                relative_coordinates[
                    "x2"
                ],
            "y2":
                relative_coordinates[
                    "y2"
                ]
        },

        "quality": metrics
    }


def evaluate_roi(roi):
    gray = cv2.cvtColor(
        roi,
        cv2.COLOR_BGR2GRAY
    )

    brightness = float(
        np.mean(gray)
    )

    sharpness = float(
        cv2.Laplacian(
            gray,
            cv2.CV_64F
        ).var()
    )

    saturated_pixels = np.sum(
        gray > 250
    )

    glare = float(
        saturated_pixels /
        gray.size *
        100
    )

    return {
        "brightness": round(
            brightness,
            2
        ),
        "sharpness": round(
            sharpness,
            2
        ),
        "glare": round(
            glare,
            2
        )
    }