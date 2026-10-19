dfrom config import (
    ROI_A,
    ROI_C
)


def extract_roi_a(image):

    x = ROI_A["x"]
    y = ROI_A["y"]
    w = ROI_A["w"]
    h = ROI_A["h"]

    return image[
        y:y+h,
        x:x+w
    ]


def extract_roi_c(image):

    x = ROI_C["x"]
    y = ROI_C["y"]
    w = ROI_C["w"]
    h = ROI_C["h"]

    return image[
        y:y+h,
        x:x+w
    ]