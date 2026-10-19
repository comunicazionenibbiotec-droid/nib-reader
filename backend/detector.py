import cv2
import numpy as np


def detect_device(image):

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    blur = cv2.GaussianBlur(
        gray,
        (7, 7),
        0
    )

    _, thresh = cv2.threshold(
        blur,
        180,
        255,
        cv2.THRESH_BINARY
    )

    contours, _ = cv2.findContours(
        thresh,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    best_contour = None
    best_area = 0

    for contour in contours:

        area = cv2.contourArea(
            contour
        )

        if area < 50000:
            continue

        x, y, w, h = cv2.boundingRect(
            contour
        )

        ratio = h / w

        if ratio < 1.5:
            continue

        if ratio > 2.5:
            continue

        if area > best_area:

            best_area = area

            best_contour = contour

    if best_contour is None:

        return None

    x, y, w, h = cv2.boundingRect(
        best_contour
    )

    cropped = image[
        y:y+h,
        x:x+w
    ]

    return {

        "image": cropped,

        "bbox": {
            "x": int(x),
            "y": int(y),
            "w": int(w),
            "h": int(h)
        }

    }