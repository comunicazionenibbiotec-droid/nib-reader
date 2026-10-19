import cv2


TARGET_RATIO = 1.85


def alignment_score(
    width,
    height
):

    ratio = height / width

    error = abs(
        ratio -
        TARGET_RATIO
    )

    score = max(
        0,
        1 - error
    )

    return round(
        score,
        3
    )


def normalize_device(image):

    return cv2.resize(
        image,
        (1000, 1800)
    )