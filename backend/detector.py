import cv2
import numpy as np


NORMALIZED_WIDTH = 800
NORMALIZED_HEIGHT = 1600


EXPECTED_DEVICE_ASPECT_RATIO = 2.02

DEVICE_MIN_ASPECT_RATIO = 1.75
DEVICE_MAX_ASPECT_RATIO = 2.25

DEVICE_MIN_AREA_RATIO = 0.03
DEVICE_MAX_AREA_RATIO = 0.35

DEVICE_THRESHOLD = 180


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

    if not isinstance(
        image,
        np.ndarray
    ):
        return None

    if image.size == 0:
        return None

    if len(image.shape) != 3:
        return None

    image_height, image_width = (
        image.shape[:2]
    )

    if (
        image_width <= 0 or
        image_height <= 0
    ):
        return None

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

    _, threshold_image = cv2.threshold(
        blurred,
        DEVICE_THRESHOLD,
        255,
        cv2.THRESH_BINARY
    )

    threshold_image = clean_threshold(
        threshold_image
    )

    contours, _ = cv2.findContours(
        threshold_image,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = []

    for contour in contours:
        candidate = evaluate_candidate(
            contour=contour,
            image_width=image_width,
            image_height=image_height,
            image_area=image_area
        )

        if candidate is not None:
            candidates.append(
                candidate
            )

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

    if (
        device_image is None or
        device_image.size == 0
    ):
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
        normalized_device=
            normalized_device,

        relative_coordinates=
            WINDOW_A_RELATIVE,

        window_name="A"
    )

    window_c = extract_window(
        normalized_device=
            normalized_device,

        relative_coordinates=
            WINDOW_C_RELATIVE,

        window_name="C"
    )

    geometry_ok = (
        window_a["detected"] and
        window_c["detected"]
    )

    device_clipped = check_device_clipped(
        x=x,
        y=y,
        width=width,
        height=height,
        image_width=image_width,
        image_height=image_height
    )

    if device_clipped:
        geometry_ok = False

    return {
        "image":
            device_image,

        "normalized_image":
            normalized_device,

        "bbox": {
            "x": int(x),
            "y": int(y),
            "w": int(width),
            "h": int(height)
        },

        "device_metrics": {
            "candidate_score": round(
                best_candidate[
                    "score"
                ],
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

            "center_score": round(
                best_candidate[
                    "center_score"
                ],
                3
            ),

            "aspect_score": round(
                best_candidate[
                    "aspect_score"
                ],
                3
            ),

            "candidate_count": len(
                candidates
            ),

            "device_clipped":
                device_clipped
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


def clean_threshold(
    threshold_image
):
    kernel_close = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (9, 9)
    )

    kernel_open = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (5, 5)
    )

    cleaned = cv2.morphologyEx(
        threshold_image,
        cv2.MORPH_CLOSE,
        kernel_close,
        iterations=2
    )

    cleaned = cv2.morphologyEx(
        cleaned,
        cv2.MORPH_OPEN,
        kernel_open,
        iterations=1
    )

    return cleaned


def evaluate_candidate(
    contour,
    image_width,
    image_height,
    image_area
):
    contour_area = cv2.contourArea(
        contour
    )

    if contour_area <= 0:
        return None

    x, y, width, height = (
        cv2.boundingRect(
            contour
        )
    )

    if (
        width <= 0 or
        height <= 0
    ):
        return None

    rectangular_area = (
        width *
        height
    )

    if rectangular_area <= 0:
        return None

    aspect_ratio = (
        height /
        width
    )

    area_ratio = (
        contour_area /
        image_area
    )

    fill_ratio = (
        contour_area /
        rectangular_area
    )

    if (
        aspect_ratio <
        DEVICE_MIN_ASPECT_RATIO
    ):
        return None

    if (
        aspect_ratio >
        DEVICE_MAX_ASPECT_RATIO
    ):
        return None

    if (
        area_ratio <
        DEVICE_MIN_AREA_RATIO
    ):
        return None

    if (
        area_ratio >
        DEVICE_MAX_AREA_RATIO
    ):
        return None

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

    if image_diagonal <= 0:
        return None

    normalized_center_distance = (
        center_distance /
        image_diagonal
    )

    center_score = max(
        0.0,
        1.0 -
        normalized_center_distance * 4
    )

    aspect_error = abs(
        aspect_ratio -
        EXPECTED_DEVICE_ASPECT_RATIO
    )

    aspect_score = max(
        0.0,
        1.0 -
        aspect_error / 0.5
    )

    fill_score = min(
        1.0,
        max(
            0.0,
            fill_ratio
        )
    )

    edge_penalty = calculate_edge_penalty(
        x=x,
        y=y,
        width=width,
        height=height,
        image_width=image_width,
        image_height=image_height
    )

    candidate_score = (
        0.45 *
        aspect_score +

        0.30 *
        center_score +

        0.25 *
        fill_score -

        edge_penalty
    )

    candidate_score = max(
        0.0,
        min(
            1.0,
            candidate_score
        )
    )

    return {
        "contour":
            contour,

        "score":
            float(
                candidate_score
            ),

        "x":
            int(x),

        "y":
            int(y),

        "w":
            int(width),

        "h":
            int(height),

        "aspect_ratio":
            float(
                aspect_ratio
            ),

        "area_ratio":
            float(
                area_ratio
            ),

        "fill_ratio":
            float(
                fill_ratio
            ),

        "center_score":
            float(
                center_score
            ),

        "aspect_score":
            float(
                aspect_score
            ),

        "edge_penalty":
            float(
                edge_penalty
            )
    }


def calculate_edge_penalty(
    x,
    y,
    width,
    height,
    image_width,
    image_height
):
    horizontal_margin = max(
      