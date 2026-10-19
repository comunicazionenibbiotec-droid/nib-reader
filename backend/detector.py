import cv2


def detect_device(image):

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    blur = cv2.GaussianBlur(
        gray,
        (5, 5),
        0
    )

    edges = cv2.Canny(
        blur,
        50,
        150
    )

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:

        return None

    largest = max(
        contours,
        key=cv2.contourArea
    )

    area = cv2.contourArea(
        largest
    )

    print("AREA:", area)

    # if area < 10000:
#     return None


    x, y, w, h = cv2.boundingRect(
        largest
    )

    cropped = image[
        y:y+h,
        x:x+w
    ]

    return {

        "image": cropped,

        "bbox": {
            "x": x,
            "y": y,
            "w": w,
            "h": h
        }

    }