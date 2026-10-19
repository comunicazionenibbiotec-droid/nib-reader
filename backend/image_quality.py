import cv2
import numpy as np


def brightness_score(image):

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    return float(
        np.mean(gray)
    )


def sharpness_score(image):

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    return float(

        cv2.Laplacian(
            gray,
            cv2.CV_64F
        ).var()

    )


def glare_score(image):

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    saturated = np.sum(
        gray > 250
    )

    total = gray.size

    return float(
        saturated / total * 100
    )


def evaluate_quality(image):

    brightness = brightness_score(
        image
    )

    sharpness = sharpness_score(
        image
    )

    glare = glare_score(
        image
    )

    accepted = True

    reasons = []

    if brightness < 80:

        accepted = False

        reasons.append(
            "too_dark"
        )

    if brightness > 220:

        accepted = False

        reasons.append(
            "too_bright"
        )

    if sharpness < 80:

        accepted = False

        reasons.append(
            "blurred"
        )

    if glare > 10:

        accepted = False

        reasons.append(
            "glare"
        )

    return {

        "accepted": accepted,

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
        ),

        "reasons": reasons

    }
