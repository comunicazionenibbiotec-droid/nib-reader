import cv2
import numpy as np

from calibration_manager import get_lot_configuration


def round_number(value, digits=3):
    return round(float(value), digits)


def analyze_windows(normalized_device, windows, lot_id=None):
    lot_configuration = get_lot_configuration(lot_id)

    roi_a = extract_roi(normalized_device, windows, "A")
    roi_c = extract_roi(normalized_device, windows, "C")

    return {
        "A": analyze_window_a(roi_a, lot_configuration),
        "C": analyze_window_c(roi_c, lot_configuration),
        "lot": {
            "lot_id": lot_configuration.get("lot_id"),
            "status": lot_configuration.get("status", "unknown"),
            "schema_version": lot_configuration.get(
                "schema_version",
                "unknown",
            ),
        },
    }


def extract_roi(normalized_device, windows, window_name):
    if normalized_device is None or normalized_device.size == 0:
        return None

    window_information = windows.get(window_name, {})
    box = window_information.get("bbox_normalized")

    if not box:
        return None

    x = int(box["x"])
    y = int(box["y"])
    width = int(box["w"])
    height = int(box["h"])

    if width <= 0 or height <= 0:
        return None

    image_height, image_width = normalized_device.shape[:2]

    x1 = max(0, min(x, image_width - 1))
    y1 = max(0, min(y, image_height - 1))
    x2 = max(x1 + 1, min(x + width, image_width))
    y2 = max(y1 + 1, min(y + height, image_height))

    roi = normalized_device[y1:y2, x1:x2]

    if roi.size == 0:
        return None

    return roi


def analyze_window_a(roi, lot_configuration):
    if roi is None or roi.size == 0:
        return {
            "analysis_ok": False,
            "reason": "empty_roi",
        }

    zinc_configuration = lot_configuration.get("zinc", {})
    blank_limits = zinc_configuration.get("blank_limits", {})

    maximum_blank_chroma = float(
        blank_limits.get("maximum_chroma", 7.0)
    )
    maximum_blank_saturation = float(
        blank_limits.get("maximum_saturation_percent", 8.0)
    )

    height, width = roi.shape[:2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 1.5)

    minimum_radius = max(12, int(min(width, height) * 0.12))
    maximum_radius = max(
        minimum_radius + 1,
        int(min(width, height) * 0.32),
    )

    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min(width, height) * 0.25,
        param1=80,
        param2=24,
        minRadius=minimum_radius,
        maxRadius=maximum_radius,
    )

    expected_x = width * 0.50
    expected_y = height * 0.50
    selected_circle = select_circle(circles, expected_x, expected_y, width, height)

    detection_method = "hough_circle"

    if selected_circle is None:
        selected_circle = (
            int(round(expected_x)),
            int(round(expected_y)),
            int(round(min(width, height) * 0.20)),
        )
        detection_method = "expected_geometry_fallback"

    center_x, center_y, radius = selected_circle
    analysis_radius = max(5, int(round(radius * 0.72)))

    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.circle(
        mask,
        (int(center_x), int(center_y)),
        int(analysis_radius),
        255,
        -1,
    )

    valid_pixels = mask > 0
    pixel_count = int(np.count_nonzero(valid_pixels))

    if pixel_count < 100:
        return {
            "analysis_ok": False,
            "reason": "insufficient_disc_pixels",
        }

    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV).astype(np.float32)

    l_values = lab[:, :, 0][valid_pixels] * (100.0 / 255.0)
    a_values = lab[:, :, 1][valid_pixels] - 128.0
    b_values = lab[:, :, 2][valid_pixels] - 128.0
    hue_values = hsv[:, :, 0][valid_pixels] * 2.0
    saturation_values = hsv[:, :, 1][valid_pixels] * (100.0 / 255.0)
    value_values = hsv[:, :, 2][valid_pixels] * (100.0 / 255.0)

    median_l = float(np.median(l_values))
    median_a = float(np.median(a_values))
    median_b = float(np.median(b_values))
    median_saturation = float(np.median(saturation_values))
    chroma = float(np.hypot(median_a, median_b))

    is_blank = (
        chroma <= maximum_blank_chroma
        or median_saturation <= maximum_blank_saturation
    )

    color_index = None

    if is_blank:
        color_state = "blank_or_unreacted"
    else:
        color_index = (median_a - median_b) / (
            abs(median_a) + abs(median_b) + 0.000001
        )

        if color_index < -0.20:
            color_state = "orange_yellow"
        elif color_index > 0.15:
            color_state = "pink_magenta"
        else:
            color_state = "intermediate"

    calibration = zinc_configuration.get("calibration", {})

    return {
        "analysis_ok": True,
        "disc_detected": detection_method == "hough_circle",
        "detection_method": detection_method,
        "disc": {
            "center_x": int(center_x),
            "center_y": int(center_y),
            "radius": int(radius),
            "analysis_radius": int(analysis_radius),
            "pixel_count": pixel_count,
        },
        "lab": {
            "L_median": round_number(median_l, 2),
            "a_median": round_number(median_a, 2),
            "b_median": round_number(median_b, 2),
            "L_std": round_number(np.std(l_values), 2),
            "a_std": round_number(np.std(a_values), 2),
            "b_std": round_number(np.std(b_values), 2),
            "chroma": round_number(chroma, 2),
        },
        "hsv": {
            "hue_median_deg": round_number(np.median(hue_values), 2),
            "saturation_median_percent": round_number(
                median_saturation,
                2,
            ),
            "value_median_percent": round_number(
                np.median(value_values),
                2,
            ),
        },
        "color_index": (
            None
            if color_index is None
            else round_number(color_index, 4)
        ),
        "color_state": color_state,
        "calibration": {
            "lot_id": lot_configuration.get("lot_id"),
            "available": bool(calibration.get("available", False)),
            "concentration": None,
            "unit": calibration.get("concentration_unit"),
        },
    }


def select_circle(circles, expected_x, expected_y, width, height):
    if circles is None:
        return None

    best_circle = None
    best_score = None
    candidates = np.round(circles[0]).astype(int)

    for center_x, center_y, radius in candidates:
        if radius <= 0:
            continue

        if center_x - radius < 0 or center_x + radius >= width:
            continue

        if center_y - radius < 0 or center_y + radius >= height:
            continue

        distance = np.hypot(
            center_x - expected_x,
            center_y - expected_y,
        )
        score = distance / max(width, height)

        if best_score is None or score < best_score:
            best_score = score
            best_circle = (
                int(center_x),
                int(center_y),
                int(radius),
            )

    return best_circle


def analyze_window_c(roi, lot_configuration):
    if roi is None or roi.size == 0:
        return {
            "analysis_ok": False,
            "reason": "empty_roi",
        }

    psa_configuration = lot_configuration.get("psa", {})
    line_geometry = psa_configuration.get("line_geometry", {})

    expected_distance = float(
        line_geometry.get("expected_distance_relative", 0.325)
    )
    distance_tolerance = float(
        line_geometry.get("distance_tolerance_relative", 0.12)
    )
    minimum_line_intensity = float(
        line_geometry.get("minimum_line_intensity", 7.0)
    )
    minimum_width_relative = float(
        line_geometry.get("minimum_line_width_relative", 0.006)
    )
    maximum_width_relative = float(
        line_geometry.get("maximum_line_width_relative", 0.12)
    )

    height, width = roi.shape[:2]

    membrane_x1 = int(round(width * 0.32))
    membrane_x2 = int(round(width * 0.68))
    membrane_y1 = int(round(height * 0.12))
    membrane_y2 = int(round(height * 0.88))

    membrane = roi[
        membrane_y1:membrane_y2,
        membrane_x1:membrane_x2,
    ]

    if (
        membrane.size == 0
        or membrane.shape[0] < 40
        or membrane.shape[1] < 15
    ):
        return {
            "analysis_ok": False,
            "reason": "invalid_membrane_roi",
        }

    lab = cv2.cvtColor(membrane, cv2.COLOR_BGR2LAB).astype(np.float32)
    bgr = membrane.astype(np.float32)

    a_signal = lab[:, :, 1] - 128.0
    red_excess = bgr[:, :, 2] - 0.5 * (
        bgr[:, :, 1] + bgr[:, :, 0]
    )

    combined_signal = np.maximum(a_signal, 0.0) + 0.35 * np.maximum(
        red_excess,
        0.0,
    )

    horizontal_margin = max(1, int(membrane.shape[1] * 0.12))
    core = combined_signal[
        :,
        horizontal_margin:membrane.shape[1] - horizontal_margin,
    ]

    raw_profile = np.median(core, axis=1)
    kernel_size = max(7, int(len(raw_profile) * 0.018))
    smoothed_profile = smooth_profile(raw_profile, kernel_size)

    baseline = float(np.median(smoothed_profile))
    mad = float(
        np.median(
            np.abs(smoothed_profile - baseline)
        )
    )
    robust_sigma = 1.4826 * mad
    threshold = max(
        baseline + 5.0 * robust_sigma,
        baseline + minimum_line_intensity,
    )

    minimum_width_pixels = max(
        2,
        int(len(smoothed_profile) * minimum_width_relative),
    )
    maximum_width_pixels = max(
        minimum_width_pixels + 1,
        int(len(smoothed_profile) * maximum_width_relative),
    )
    merge_gap = max(2, int(len(smoothed_profile) * 0.018))

    regions = find_line_regions(
        smoothed_profile,
        threshold,
        minimum_width_pixels,
        maximum_width_pixels,
        merge_gap,
    )

    lines = build_line_list(
        smoothed_profile,
        baseline,
        regions,
    )

    test_candidates = [
        line
        for line in lines
        if line["position_relative"] < 0.50
    ]
    control_candidates = [
        line
        for line in lines
        if line["position_relative"] >= 0.50
    ]

    test_line = select_strongest_line(test_candidates)
    control_line = select_strongest_line(control_candidates)

    test_line_present = test_line is not None
    control_line_present = control_line is not None

    observed_distance = None
    distance_valid = None

    if test_line_present and control_line_present:
        observed_distance = (
            control_line["position_relative"]
            - test_line["position_relative"]
        )
        distance_valid = (
            abs(observed_distance - expected_distance)
            <= distance_tolerance
        )

    test_valid = control_line_present

    if distance_valid is False:
        test_valid = False

    if not control_line_present:
        if test_line_present:
            test_state = "invalid_missing_control_line"
        else:
            test_state = "not_run_or_invalid"
    elif not test_line_present:
        test_state = "one_line"
    elif distance_valid is False:
        test_state = "invalid_line_spacing"
    else:
        test_state = "two_lines"

    test_control_ratio = None

    if (
        test_line_present
        and control_line_present
        and control_line["intensity"] > 0
    ):
        test_control_ratio = (
            test_line["intensity"]
            / control_line["intensity"]
        )

    selected_lines = []

    if test_line is not None:
        selected_lines.append(test_line)

    if control_line is not None:
        selected_lines.append(control_line)

    unassigned_lines = [
        line
        for line in lines
        if line not in selected_lines
    ]

    calibration = psa_configuration.get("calibration", {})

    return {
        "analysis_ok": True,
        "membrane_detected": True,
        "detection_method": "normalized_geometry",
        "membrane_bbox": {
            "x": int(membrane_x1),
            "y": int(membrane_y1),
            "w": int(membrane_x2 - membrane_x1),
            "h": int(membrane_y2 - membrane_y1),
        },
        "profile": {
            "baseline": round_number(baseline, 2),
            "mad": round_number(mad, 2),
            "threshold": round_number(threshold, 2),
            "length": int(len(smoothed_profile)),
        },
        "detected_line_count": len(lines),
        "detected_lines": lines,
        "test_line": test_line,
        "control_line": control_line,
        "unassigned_lines": unassigned_lines,
        "test_line_present": test_line_present,
        "control_line_present": control_line_present,
        "expected_distance_relative": round_number(
            expected_distance,
            4,
        ),
        "observed_distance_relative": (
            None
            if observed_distance is None
            else round_number(observed_distance, 4)
        ),
        "distance_valid": distance_valid,
        "test_control_ratio": (
            None
            if test_control_ratio is None
            else round_number(test_control_ratio, 4)
        ),
        "test_valid": test_valid,
        "test_state": test_state,
        "calibration": {
            "lot_id": lot_configuration.get("lot_id"),
            "available": bool(calibration.get("available", False)),
            "concentration": None,
            "unit": calibration.get("concentration_unit"),
        },
    }


def smooth_profile(profile, kernel_size):
    kernel_size = max(3, int(kernel_size))

    if kernel_size % 2 == 0:
        kernel_size += 1

    kernel = np.ones(kernel_size, dtype=np.float32) / kernel_size
    return np.convolve(profile, kernel, mode="same")


def find_line_regions(
    signal,
    threshold,
    minimum_width,
    maximum_width,
    merge_gap,
):
    active = signal >= threshold
    regions = []
    start = None

    for index, flag in enumerate(active):
        is_last = index == len(active) - 1

        if flag and start is None:
            start = index

        if start is not None and (not flag or is_last):
            end = index if flag and is_last else index - 1
            width = end - start + 1

            if minimum_width <= width <= maximum_width:
                regions.append([start, end])

            start = None

    merged = []

    for region in regions:
        if not merged:
            merged.append(region)
            continue

        gap = region[0] - merged[-1][1]

        if gap > merge_gap:
            merged.append(region)
        else:
            merged[-1][1] = region[1]

    return merged


def build_line_list(profile, baseline, regions):
    lines = []
    profile_length = len(profile)

    for start, end in regions:
        segment = profile[start:end + 1]
        peak_y = start + int(np.argmax(segment))
        intensity = float(profile[peak_y] - baseline)
        position = peak_y / max(1, profile_length - 1)

        if position < 0.05 or position > 0.95:
            continue

        width_pixels = end - start + 1

        lines.append(
            {
                "position_relative": round_number(position, 4),
                "position_y": int(peak_y),
                "width_px": int(width_pixels),
                "width_relative": round_number(
                    width_pixels / profile_length,
                    4,
                ),
                "intensity": round_number(intensity, 2),
                "start_y": int(start),
                "end_y": int(end),
            }
        )

    return lines


def select_strongest_line(lines):
    if not lines:
        return None

    return max(
        lines,
        key=lambda line: line["intensity"],
    )
