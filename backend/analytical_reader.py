import cv2
import numpy as np


def _round(value, digits=3):
    return round(float(value), digits)


def analyze_window_a(roi):
    if roi is None or roi.size == 0:
        return {"analysis_ok": False, "reason": "empty_roi"}

    height, width = roi.shape[:2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 1.5)

    min_radius = max(12, int(min(width, height) * 0.12))
    max_radius = max(min_radius + 1, int(min(width, height) * 0.32))

    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min(width, height) * 0.25,
        param1=80,
        param2=24,
        minRadius=min_radius,
        maxRadius=max_radius,
    )

    expected_x = width * 0.50
    expected_y = height * 0.50
    selected = None

    if circles is not None:
        candidates = np.round(circles[0]).astype(int)
        best_score = None
        for center_x, center_y, radius in candidates:
            if radius <= 0:
                continue
            distance = np.hypot(center_x - expected_x, center_y - expected_y)
            score = distance / max(width, height)
            if best_score is None or score < best_score:
                best_score = score
                selected = (center_x, center_y, radius)

    detection_method = "hough_circle"
    if selected is None:
        selected = (
            int(round(expected_x)),
            int(round(expected_y)),
            int(round(min(width, height) * 0.20)),
        )
        detection_method = "expected_geometry_fallback"

    center_x, center_y, radius = selected
    analysis_radius = max(5, int(round(radius * 0.72)))

    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.circle(mask, (center_x, center_y), analysis_radius, 255, -1)

    valid_pixels = mask > 0
    pixel_count = int(np.count_nonzero(valid_pixels))
    if pixel_count < 100:
        return {"analysis_ok": False, "reason": "insufficient_disc_pixels"}

    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV).astype(np.float32)

    l_values = lab[:, :, 0][valid_pixels] * (100.0 / 255.0)
    a_values = lab[:, :, 1][valid_pixels] - 128.0
    b_values = lab[:, :, 2][valid_pixels] - 128.0
    hue_values = hsv[:, :, 0][valid_pixels] * 2.0
    saturation_values = hsv[:, :, 1][valid_pixels] * (100.0 / 255.0)
    value_values = hsv[:, :, 2][valid_pixels] * (100.0 / 255.0)

    median_a = float(np.median(a_values))
    median_b = float(np.median(b_values))
    median_saturation = float(np.median(saturation_values))
    chroma = float(np.sqrt(median_a ** 2 + median_b ** 2))

    if median_saturation < 8.0 or chroma < 7.0:
        color_state = "blank_or_unreacted"
    elif median_a >= 12.0 and median_b <= 15.0:
        color_state = "pink_magenta"
    elif median_b >= 15.0 and median_a >= 2.0:
        color_state = "orange_yellow"
    else:
        color_state = "intermediate"

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
            "L_median": _round(np.median(l_values), 2),
            "a_median": _round(median_a, 2),
            "b_median": _round(median_b, 2),
            "L_std": _round(np.std(l_values), 2),
            "a_std": _round(np.std(a_values), 2),
            "b_std": _round(np.std(b_values), 2),
            "chroma": _round(chroma, 2),
        },
        "hsv": {
            "hue_median_deg": _round(np.median(hue_values), 2),
            "saturation_median_percent": _round(median_saturation, 2),
            "value_median_percent": _round(np.median(value_values), 2),
        },
        "color_state": color_state,
    }


def _longest_true_run(values):
    best_start = None
    best_end = None
    start = None
    for index, flag in enumerate(values):
        if flag and start is None:
            start = index
        if start is not None and (not flag or index == len(values) - 1):
            end = index if flag and index == len(values) - 1 else index - 1
            if best_start is None or end - start > best_end - best_start:
                best_start, best_end = start, end
            start = None
    return best_start, best_end


def _detect_membrane(roi):
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0]
    height, width = l_channel.shape

    central = l_channel[int(height * 0.08):int(height * 0.92), int(width * 0.18):int(width * 0.82)]
    threshold = max(150, int(np.percentile(central, 65)))
    bright = l_channel >= threshold

    column_fraction = bright.mean(axis=0)
    row_fraction = bright.mean(axis=1)

    column_mask = column_fraction >= 0.32
    row_mask = row_fraction >= 0.12

    x1, x2 = _longest_true_run(column_mask)
    y1, y2 = _longest_true_run(row_mask)

    if x1 is None or y1 is None:
        return None

    membrane_width = x2 - x1 + 1
    membrane_height = y2 - y1 + 1

    if membrane_width < width * 0.12 or membrane_height < height * 0.25:
        return None

    return int(x1), int(y1), int(x2 + 1), int(y2 + 1)


def _smooth_profile(profile, kernel_size=11):
    kernel_size = max(3, int(kernel_size))
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = np.ones(kernel_size, dtype=np.float32) / kernel_size
    return np.convolve(profile, kernel, mode="same")


def _find_line_regions(signal, threshold, min_width, merge_gap):
    active = signal >= threshold
    regions = []
    start = None

    for index, flag in enumerate(active):
        if flag and start is None:
            start = index
        if start is not None and (not flag or index == len(active) - 1):
            end = index if flag and index == len(active) - 1 else index - 1
            if end - start + 1 >= min_width:
                regions.append([start, end])
            start = None

    merged = []
    for region in regions:
        if not merged or region[0] - merged[-1][1] > merge_gap:
            merged.append(region)
        else:
            merged[-1][1] = region[1]
    return merged


def analyze_window_c(roi):
    if roi is None or roi.size == 0:
        return {"analysis_ok": False, "reason": "empty_roi"}

    height, width = roi.shape[:2]

    # The normalized cassette geometry is fixed. A conservative internal crop
    # is more stable than brightness segmentation, because red lines split the
    # bright membrane and can shorten the detected component.
    x1 = int(round(width * 0.32))
    x2 = int(round(width * 0.68))
    y1 = int(round(height * 0.12))
    y2 = int(round(height * 0.88))

    membrane = roi[y1:y2, x1:x2]
    if membrane.size == 0 or membrane.shape[0] < 40 or membrane.shape[1] < 15:
        return {"analysis_ok": False, "reason": "invalid_membrane_roi"}

    lab = cv2.cvtColor(membrane, cv2.COLOR_BGR2LAB).astype(np.float32)
    bgr = membrane.astype(np.float32)

    a_signal = lab[:, :, 1] - 128.0
    red_excess = bgr[:, :, 2] - 0.5 * (bgr[:, :, 1] + bgr[:, :, 0])
    combined = np.maximum(a_signal, 0.0) + 0.35 * np.maximum(red_excess, 0.0)

    horizontal_margin = max(1, int(membrane.shape[1] * 0.12))
    core = combined[:, horizontal_margin:membrane.shape[1] - horizontal_margin]
    profile = np.median(core, axis=1)
    smooth = _smooth_profile(profile, max(7, int(len(profile) * 0.018)))

    baseline = float(np.median(smooth))
    mad = float(np.median(np.abs(smooth - baseline)))
    robust_sigma = 1.4826 * mad
    threshold = max(baseline + 5.0 * robust_sigma, baseline + 7.0)

    min_width = max(2, int(len(smooth) * 0.008))
    merge_gap = max(2, int(len(smooth) * 0.018))
    regions = _find_line_regions(smooth, threshold, min_width, merge_gap)

    lines = []
    for start, end in regions:
        segment = smooth[start:end + 1]
        peak_y = start + int(np.argmax(segment))
        intensity = float(smooth[peak_y] - baseline)
        position = peak_y / max(1, len(smooth) - 1)
        # Reject edge artifacts; valid lines must be inside the membrane.
        if position < 0.08 or position > 0.92:
            continue
        lines.append({
            "position_relative": _round(position, 4),
            "position_y": int(peak_y),
            "width_px": int(end - start + 1),
            "intensity": _round(intensity, 2),
            "start_y": int(start),
            "end_y": int(end),
        })

    if len(lines) > 2:
        lines = sorted(lines, key=lambda item: item["intensity"], reverse=True)[:2]
    lines.sort(key=lambda item: item["position_relative"])

    line_count = len(lines)
    if line_count == 0:
        test_state = "not_run_or_invalid"
    elif line_count == 1:
        test_state = "one_line"
    else:
        test_state = "two_lines"

    return {
        "analysis_ok": True,
        "membrane_detected": True,
        "detection_method": "normalized_geometry",
        "membrane_bbox": {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1},
        "profile": {
            "baseline": _round(baseline, 2),
            "mad": _round(mad, 2),
            "threshold": _round(threshold, 2),
            "length": int(len(smooth)),
        },
        "line_count": int(line_count),
        "lines": lines,
        "control_line_present": line_count >= 1,
        "test_line_present": line_count >= 2,
        "test_valid": line_count >= 1,
        "test_state": test_state,
    }

def analyze_windows(normalized_device, windows):
    results = {}
    for name, analyzer in (("A", analyze_window_a), ("C", analyze_window_c)):
        info = windows.get(name, {})
        box = info.get("bbox_normalized")
        if not box:
            results[name] = {"analysis_ok": False, "reason": "missing_bbox"}
            continue
        x = int(box["x"])
        y = int(box["y"])
        w = int(box["w"])
        h = int(box["h"])
        roi = normalized_device[y:y + h, x:x + w]
        results[name] = analyzer(roi)
    return results
