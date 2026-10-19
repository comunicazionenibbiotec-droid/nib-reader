import cv2
import numpy as np
from scipy.signal import find_peaks


def analyze_lateral_flow(roi):

    gray = cv2.cvtColor(
        roi,
        cv2.COLOR_BGR2GRAY
    )

    profile =
        np.mean(
            gray,
            axis=1
        )

    signal =
        255 - profile

    peaks, _ =
        find_peaks(
            signal,
            distance=30,
            prominence=5
        )

    control_line =
        len(peaks) >= 1

    test_line =
        len(peaks) >= 2

    IC = 0
    IT = 0

    if len(peaks) >= 1:

        IC =
            float(
                signal[
                    peaks[-1]
                ]
            )

    if len(peaks) >= 2:

        IT =
            float(
                signal[
                    peaks[0]
                ]
            )

    ratio = 0

    if IC > 0:

        ratio =
            IT / IC

    return {

        "control_line":control_line,

        "test_line":test_line,

        "IC":round(IC,2),

        "IT":round(IT,2),

        "ratio":round(ratio,4)

    }