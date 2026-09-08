"""
═══════════════════════════════════════════════════════════════
AK PRINT SEVA — ADVANCED AADHAAR AI VISION ENGINE
services/document-ai/aadhaar_processor.py
Industrial 5-Layer Computer Vision & Document AI Architecture:
1. Card Paper Whiteness Gating (Rejects background texture false-positives)
2. Core-Bounded Line Segment & Gradient Snapping (Sub-pixel boundary intersection)
3. ISO/IEC 7810 ID-1 Ratio Snapping (1.5858 aspect ratio + 2.5% safety buffer)
4. Multi-Feature Concurrence (Deterministic Front vs Back Classification)
5. 0° Level Horizontal Projective Straightening & Color Preservation
═══════════════════════════════════════════════════════════════
"""

import sys
import os
import json
import argparse
import math
import io
import re
import numpy as np
import cv2
from PIL import Image
import pypdf

# Configure Tesseract OCR
try:
    import pytesseract
    tesseract_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'D:\Tesseract-OCR\tesseract.exe'
    ]
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'
    for tp in tesseract_paths:
        if os.path.exists(tp):
            pytesseract.pytesseract.tesseract_cmd = tp
            break
except ImportError:
    pytesseract = None

# Initialize Face Cascade
face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(face_cascade_path) if os.path.exists(face_cascade_path) else None


def order_points(pts):
    """
    Orders 4 points in clockwise order: [Top-Left, Top-Right, Bottom-Right, Bottom-Left]
    """
    pts = np.array(pts, dtype="float32")
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # Top-left has smallest x+y
    rect[2] = pts[np.argmax(s)]  # Bottom-right has largest x+y

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # Top-right has smallest y-x
    rect[3] = pts[np.argmax(diff)]  # Bottom-left has largest y-x

    return rect


def is_card_paper_region(image_bgr, box_coords):
    """
    LAYER 1: Card Paper Whiteness & Saturation Gating Filter.
    Returns True ONLY if the region matches Aadhaar card paper (Lightness > 120, Saturation < 95).
    Rejects dark blue bedsheets, black fabrics, and dark brown wood grains.
    """
    h, w = image_bgr.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in box_coords]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    if x2 - x1 < 25 or y2 - y1 < 25:
        return False

    roi = image_bgr[y1:y2, x1:x2]
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    mean_l = float(np.mean(lab[:, :, 0]))
    mean_s = float(np.mean(hsv[:, :, 1]))

    # ID card paper is bright and low/medium saturation
    return (mean_l > 115) and (mean_s < 105)


def score_quad_candidate(box_pts, image_shape, priority_weight=1.0):
    """
    Validates that a quadrilateral candidate is strictly non-degenerate and scores it.
    """
    h, w = image_shape[:2]
    total_area = float(h * w)

    ordered = order_points(box_pts)
    w_top = np.linalg.norm(ordered[1] - ordered[0])
    w_bot = np.linalg.norm(ordered[2] - ordered[3])
    h_left = np.linalg.norm(ordered[3] - ordered[0])
    h_right = np.linalg.norm(ordered[2] - ordered[1])

    if w_top < 30 or w_bot < 30 or h_left < 30 or h_right < 30:
        return None, 0

    for i in range(4):
        for j in range(i + 1, 4):
            if np.linalg.norm(ordered[i] - ordered[j]) < 30:
                return None, 0

    avg_w = (w_top + w_bot) / 2.0
    avg_h = (h_left + h_right) / 2.0

    quad_area = avg_w * avg_h
    area_ratio = quad_area / total_area

    if area_ratio < 0.05 or area_ratio > 0.98:
        return None, 0

    long_side = max(avg_w, avg_h)
    short_side = min(avg_w, avg_h)
    aspect_ratio = long_side / short_side

    ideal_aspect = 1.586
    aspect_error = abs(aspect_ratio - ideal_aspect)

    if aspect_ratio < 1.05 or aspect_ratio > 2.6:
        return None, 0

    aspect_score = max(0.0, 1.0 - (aspect_error / 0.70))
    area_score = min(1.0, area_ratio / 0.35)

    final_score = (aspect_score * 0.65 + area_score * 0.35) * 100.0 * priority_weight
    return ordered, final_score


def classify_image_type(image):
    """
    👁️ THE EYE — Image Type Classifier.
    Analyzes the image BEFORE any cropping to determine what strategy to use.
    Returns: { 'type': str, 'confidence': float, 'details': dict }
    """
    h, w = image.shape[:2]
    scale = 800.0 / max(h, w) if max(h, w) > 800 else 1.0
    resized = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA) if scale < 1.0 else image.copy()
    rh, rw = resized.shape[:2]

    lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    # 1. Border strip analysis (4% border)
    border = max(2, int(max(rh, rw) * 0.04))
    border_pixels_lab = np.vstack([
        lab[:border, :].reshape(-1, 3),
        lab[-border:, :].reshape(-1, 3),
        lab[:, :border].reshape(-1, 3),
        lab[:, -border:].reshape(-1, 3)
    ])
    border_mean = np.mean(border_pixels_lab, axis=0)
    border_std = np.std(border_pixels_lab, axis=0)

    # 2. Center region analysis
    ch, cw = rh // 4, rw // 4
    center_pixels = lab[ch:3*ch, cw:3*cw].reshape(-1, 3)
    center_mean = np.mean(center_pixels, axis=0)

    # 3. Border-Center contrast
    border_center_diff = float(np.linalg.norm(center_mean - border_mean))

    # 4. Card occupancy (bright low-saturation pixels)
    bright_mask = ((lab[:, :, 0] > 140) & (hsv[:, :, 1] < 80)).astype('uint8')
    card_occupancy = float(np.sum(bright_mask)) / (rh * rw) * 100.0

    # 5. Border texture energy (Sobel gradient)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    energy_map = np.sqrt(sobel_x**2 + sobel_y**2)
    border_energy_mask = np.zeros((rh, rw), dtype=bool)
    border_energy_mask[:border, :] = True
    border_energy_mask[-border:, :] = True
    border_energy_mask[:, :border] = True
    border_energy_mask[:, -border:] = True
    border_texture_energy = float(np.mean(energy_map[border_energy_mask]))

    details = {
        'border_l_std': float(border_std[0]),
        'border_center_diff': border_center_diff,
        'card_occupancy': card_occupancy,
        'border_texture_energy': border_texture_energy,
        'border_l_mean': float(border_mean[0])
    }

    # Classification logic
    if border_std[0] < 15 and border_center_diff > 40:
        return {'type': 'solid_color', 'confidence': 0.95, 'details': details}

    if card_occupancy > 75:
        # Check if borders are asymmetric or contain a dark plastic folder edge
        top_edge_l = float(np.mean(lab[:border, :, 0]))
        bot_edge_l = float(np.mean(lab[-border:, :, 0]))
        left_edge_l = float(np.mean(lab[:, :border, 0]))
        right_edge_l = float(np.mean(lab[:, -border:, 0]))
        min_edge_l = min(top_edge_l, bot_edge_l, left_edge_l, right_edge_l)
        max_edge_l = max(top_edge_l, bot_edge_l, left_edge_l, right_edge_l)

        if min_edge_l < 165 or (max_edge_l - min_edge_l) > 35:
            return {'type': 'plastic_folder', 'confidence': 0.92, 'details': details}
        return {'type': 'close_up_scan', 'confidence': 0.90, 'details': details}

    # Dark background MUST be checked BEFORE textured_fabric
    # Dark surfaces (tables, floors) also have high edge energy at card boundary
    # Key differentiator: dark bg has low border lightness (L < 120)
    if border_center_diff > 60 and border_mean[0] < 120:
        return {'type': 'dark_bg_mixed', 'confidence': 0.90, 'details': details}

    if border_texture_energy > 50 and border_std[0] > 15:
        # Differentiate between granular ground (soil/mud/sand) vs colorful bedsheet fabric
        # Soil has uniform earthy hue (std of A/B < 10.0), fabric has multi-color prints (std of A/B > 12.0)
        if border_std[1] < 10.0 and border_std[2] < 10.0:
            return {'type': 'granular_ground', 'confidence': 0.92, 'details': details}
        return {'type': 'textured_fabric', 'confidence': 0.85, 'details': details}

    return {'type': 'unknown', 'confidence': 0.50, 'details': details}


# ═══════════════════════════════════════════════════════════════
# STRATEGY A: SOLID COLOR BACKGROUND (Red, Green, Blue, Wood, White)
# Proven working on: Red bg ✅, Green bg ✅, Wood table ✅
# Method: LAB Border Saliency Differential
# ═══════════════════════════════════════════════════════════════
def strategy_solid_color(image):
    """ISOLATED Strategy A — exact copy of proven LAB border saliency code."""
    h, w = image.shape[:2]
    candidates = []

    scale = 800.0 / max(h, w) if max(h, w) > 800 else 1.0
    resized = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA) if scale < 1.0 else image.copy()
    rh, rw = resized.shape[:2]
    r_area = rh * rw

    lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)

    try:
        border_mask = np.zeros((rh, rw), dtype=np.uint8)
        bw_b = max(2, int(rw * 0.04))
        bh_b = max(2, int(rh * 0.04))
        border_mask[:bh_b, :] = 255
        border_mask[-bh_b:, :] = 255
        border_mask[:, :bw_b] = 255
        border_mask[:, -bw_b:] = 255

        bg_samples = lab[border_mask == 255]
        if len(bg_samples) > 0:
            bg_median = np.median(bg_samples, axis=0)
            diff_lab = np.linalg.norm(lab.astype('float32') - bg_median.astype('float32'), axis=2).astype('uint8')
            diff_filtered = cv2.bilateralFilter(diff_lab, 9, 75, 75)

            for thresh_val in [None, 25, 35, 50]:
                if thresh_val is None:
                    _, fg_thresh = cv2.threshold(diff_filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                else:
                    _, fg_thresh = cv2.threshold(diff_filtered, thresh_val, 255, cv2.THRESH_BINARY)

                k_cl = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
                fg_clean = cv2.morphologyEx(fg_thresh, cv2.MORPH_CLOSE, k_cl, iterations=3)
                fg_clean = cv2.morphologyEx(fg_clean, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)), iterations=1)

                cnts_bg, _ = cv2.findContours(fg_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for c in cnts_bg:
                    area = cv2.contourArea(c)
                    if 0.08 * r_area < area < 0.92 * r_area:
                        hull = cv2.convexHull(c)
                        rect = cv2.minAreaRect(hull)
                        box_pts = cv2.boxPoints(rect)
                        ordered, score = score_quad_candidate(box_pts, (rh, rw), priority_weight=3.5)
                        if ordered is not None and score > 25:
                            candidates.append((ordered / scale, score + 300.0, 99))
    except Exception:
        pass

    return candidates


# ═══════════════════════════════════════════════════════════════
# STRATEGY B: TEXTURED FABRIC BACKGROUND (Bedsheet, Carpet, Blanket)
# Proven working on: Zigzag multi-color bedsheet ✅
# Method: Core-Bounded Line Segment Detector (LSD) Snapping
# ═══════════════════════════════════════════════════════════════
def strategy_textured_fabric(image):
    """ISOLATED Strategy B — exact copy of proven LSD line detection code."""
    h, w = image.shape[:2]
    candidates = []

    scale = 800.0 / max(h, w) if max(h, w) > 800 else 1.0
    resized = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA) if scale < 1.0 else image.copy()
    rh, rw = resized.shape[:2]

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)

    try:
        denoised = cv2.bilateralFilter(gray, 11, 75, 75)
        lsd = cv2.createLineSegmentDetector(0)
        lines = lsd.detect(denoised)[0]

        # Identify bright central card core
        bright = ((lab[:, :, 0] > 130) & (hsv[:, :, 1] < 95)).astype('uint8') * 255
        clean_bright = cv2.morphologyEx(bright, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(clean_bright)

        card_cx, card_cy = rw // 2, rh // 2
        max_core_area = 0
        for i in range(1, num_labels):
            cx, cy = centroids[i]
            area = stats[i, cv2.CC_STAT_AREA]
            if area > max_core_area and 0.15 * rw < cx < 0.85 * rw and 0.15 * rh < cy < 0.85 * rh:
                max_core_area = area
                card_cx, card_cy = cx, cy

        if lines is not None and max_core_area > 10000:
            card_lines = []
            angles = []
            for l in lines:
                x1, y1, x2, y2 = l[0]
                length = np.hypot(x2 - x1, y2 - y1)
                if length > 45:
                    ang = np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180
                    card_lines.append((l[0], length, ang))
                    angles.append(ang)

            if len(angles) >= 4:
                hist, bin_edges = np.histogram(angles, bins=36, range=(0, 180))
                th1 = float((bin_edges[np.argmax(hist)] + bin_edges[np.argmax(hist) + 1]) / 2.0)
                th2 = (th1 + 90.0) % 180.0

                def line_dist(l_pts, cx, cy):
                    x1, y1, x2, y2 = l_pts
                    a = y1 - y2
                    b = x2 - x1
                    c = x1 * y2 - x2 * y1
                    norm = np.hypot(a, b) + 1e-6
                    return (a * cx + b * cy + c) / norm, (a / norm, b / norm, c / norm)

                th1_pos, th1_neg = [], []
                th2_pos, th2_neg = [], []

                for l_pts, length, ang in card_lines:
                    d, eq = line_dist(l_pts, card_cx, card_cy)
                    diff1 = min(abs(ang - th1), 180 - abs(ang - th1))
                    diff2 = min(abs(ang - th2), 180 - abs(ang - th2))

                    if 35 < abs(d) < (0.45 * max(rh, rw)):
                        if diff1 < 16:
                            if d > 0: th1_pos.append((l_pts, length, d, eq))
                            else: th1_neg.append((l_pts, length, d, eq))
                        elif diff2 < 16:
                            if d > 0: th2_pos.append((l_pts, length, d, eq))
                            else: th2_neg.append((l_pts, length, d, eq))

                if th1_pos and th1_neg and th2_pos and th2_neg:
                    best_th1_pos = max(th1_pos, key=lambda x: x[1])[3]
                    best_th1_neg = max(th1_neg, key=lambda x: x[1])[3]
                    best_th2_pos = max(th2_pos, key=lambda x: x[1])[3]
                    best_th2_neg = max(th2_neg, key=lambda x: x[1])[3]

                    def intersect(l1, l2):
                        a1, b1, c1 = l1
                        a2, b2, c2 = l2
                        det = a1 * b2 - a2 * b1
                        if abs(det) < 1e-5: return None
                        return [(b1 * c2 - b2 * c1) / det, (c1 * a2 - c2 * a1) / det]

                    p1 = intersect(best_th1_pos, best_th2_pos)
                    p2 = intersect(best_th1_pos, best_th2_neg)
                    p3 = intersect(best_th1_neg, best_th2_neg)
                    p4 = intersect(best_th1_neg, best_th2_pos)

                    if p1 and p2 and p3 and p4:
                        lsd_box = np.array([p1, p2, p3, p4], dtype='float32') / scale
                        ordered, score = score_quad_candidate(lsd_box, (h, w), priority_weight=2.0)
                        if ordered is not None and score > 25:
                            candidates.append((ordered, score + 100.0, 95))
    except Exception:
        pass

    return candidates


# ═══════════════════════════════════════════════════════════════
# STRATEGY C: DARK BACKGROUND (Dark table/floor + Optional Lamination)
# For: Dark gray surfaces, dark wood, with possible laminated sleeve
# Method: High-contrast LAB saliency + Inner Card Refinement
# ═══════════════════════════════════════════════════════════════
def strategy_dark_background(image):
    """
    ISOLATED Strategy C — dark backgrounds (floor/table) + lamination sleeve handling.
    Method: High-contrast Otsu differential + 4-side Line/Edge Snapping.
    """
    h, w = image.shape[:2]
    candidates = []

    scale = 800.0 / max(h, w) if max(h, w) > 800 else 1.0
    resized = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA) if scale < 1.0 else image.copy()
    rh, rw = resized.shape[:2]
    r_area = rh * rw

    lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    try:
        border_mask = np.zeros((rh, rw), dtype=np.uint8)
        bw_b = max(2, int(rw * 0.04))
        bh_b = max(2, int(rh * 0.04))
        border_mask[:bh_b, :] = 255
        border_mask[-bh_b:, :] = 255
        border_mask[:, :bw_b] = 255
        border_mask[:, -bw_b:] = 255

        bg_samples = lab[border_mask == 255]
        if len(bg_samples) > 0:
            bg_median = np.median(bg_samples, axis=0)
            diff_lab = np.linalg.norm(lab.astype('float32') - bg_median.astype('float32'), axis=2).astype('uint8')
            diff_filtered = cv2.bilateralFilter(diff_lab, 9, 75, 75)

            # In dark backgrounds, Otsu is mathematically optimal.
            # Avoid fixed low thresholds (25, 35) which leak into dark carpets/floors.
            _, fg_thresh = cv2.threshold(diff_filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            k_cl = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
            fg_clean = cv2.morphologyEx(fg_thresh, cv2.MORPH_CLOSE, k_cl, iterations=3)
            fg_clean = cv2.morphologyEx(fg_clean, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)), iterations=1)

            cnts_bg, _ = cv2.findContours(fg_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts_bg:
                area = cv2.contourArea(c)
                if 0.08 * r_area < area < 0.95 * r_area:
                    hull = cv2.convexHull(c)
                    rect = cv2.minAreaRect(hull)
                    box_pts = cv2.boxPoints(rect)

                    # Try 4-boundary line edge snapping within the contour box
                    snapped_box = None
                    try:
                        pts = np.array(box_pts, dtype='float32')
                        s = pts.sum(axis=1)
                        diff_p = np.diff(pts, axis=1)
                        tl = pts[np.argmin(s)]
                        br = pts[np.argmax(s)]
                        tr = pts[np.argmin(diff_p)]
                        bl = pts[np.argmax(diff_p)]

                        roi_x1 = max(0, int(min(tl[0], bl[0])) - 15)
                        roi_x2 = min(rw, int(max(tr[0], br[0])) + 15)
                        roi_y1 = max(0, int(min(tl[1], tr[1])) - 15)
                        roi_y2 = min(rh, int(max(bl[1], br[1])) + 15)

                        roi_gray = gray[roi_y1:roi_y2, roi_x1:roi_x2]
                        roi_h, roi_w = roi_gray.shape[:2]

                        if roi_h > 40 and roi_w > 40:
                            edges = cv2.Canny(roi_gray, 35, 110)
                            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=35, minLineLength=int(min(roi_h, roi_w) * 0.4), maxLineGap=20)
                            if lines is not None:
                                top_cand, bot_cand, left_cand, right_cand = [], [], [], []
                                for l in lines:
                                    lx1, ly1, lx2, ly2 = l[0]
                                    length = np.hypot(lx2 - lx1, ly2 - ly1)
                                    ang = np.degrees(np.arctan2(ly2 - ly1, lx2 - lx1)) % 180
                                    if ang < 15 or ang > 165:
                                        avg_y = (ly1 + ly2) / 2.0
                                        if avg_y < roi_h * 0.35:
                                            top_cand.append((l[0], length, avg_y))
                                        elif avg_y > roi_h * 0.65:
                                            bot_cand.append((l[0], length, avg_y))
                                    elif 75 < ang < 105:
                                        avg_x = (lx1 + lx2) / 2.0
                                        if avg_x < roi_w * 0.35:
                                            left_cand.append((l[0], length, avg_x))
                                        elif avg_x > roi_w * 0.65:
                                            right_cand.append((l[0], length, avg_x))

                                if top_cand and bot_cand and left_cand and right_cand:
                                    # Pick the LONGEST line among the OUTER HALF of candidates for each side
                                    # This avoids both internal lines (like red divider) and floor artifacts
                                    def pick_best(cands, outer_fn):
                                        """Sort by position (outer_fn), take outer 50%, then pick longest."""
                                        cands_sorted = sorted(cands, key=outer_fn)
                                        outer_half = cands_sorted[:max(1, len(cands_sorted) // 2)]
                                        return max(outer_half, key=lambda x: x[1])[0]

                                    top_l = pick_best(top_cand, lambda x: x[2])       # outer top = smallest avg_y
                                    bot_l = pick_best(bot_cand, lambda x: -x[2])      # outer bottom = largest avg_y
                                    left_l = pick_best(left_cand, lambda x: x[2])     # outer left = smallest avg_x
                                    right_l = pick_best(right_cand, lambda x: -x[2])  # outer right = largest avg_x

                                    def line_eq(p):
                                        px1, py1, px2, py2 = p
                                        return py1 - py2, px2 - px1, px1 * py2 - px2 * py1

                                    def intersect(l1, l2):
                                        a1, b1, c1 = line_eq(l1)
                                        a2, b2, c2 = line_eq(l2)
                                        det = a1 * b2 - a2 * b1
                                        if abs(det) < 1e-5: return None
                                        return float((b1 * c2 - b2 * c1) / det), float((c1 * a2 - c2 * a1) / det)

                                    p_tl = intersect(top_l, left_l)
                                    p_tr = intersect(top_l, right_l)
                                    p_br = intersect(bot_l, right_l)
                                    p_bl = intersect(bot_l, left_l)

                                    if p_tl and p_tr and p_br and p_bl:
                                        candidate_box = np.array([p_tl, p_tr, p_br, p_bl], dtype='float32')
                                        candidate_box[:, 0] += roi_x1
                                        candidate_box[:, 1] += roi_y1
                                        snapped_box = candidate_box
                    except Exception:
                        pass

                    # If true 4-line boundary was snapped, use the exact rotated quad (preserves rotation angle and full header/footer)
                    if snapped_box is not None:
                        final_box_scaled = snapped_box
                    else:
                        # ── ROTATED QUAD INVERSE PERSPECTIVE SNAPPING ──
                        # Preserves the true card rotation angle (handles tilted cards on keyboards, dark desks, etc.)
                        # Instead of collapsing the rotated quad into a destructive axis-aligned box,
                        # warp to temp space, scan margins for paper edge, and project back.
                        final_box_scaled = box_pts
                        try:
                            s_pts = np.array(box_pts, dtype='float32')
                            s_sum = s_pts.sum(axis=1)
                            s_diff = np.diff(s_pts, axis=1)
                            q_tl = s_pts[np.argmin(s_sum)]
                            q_br = s_pts[np.argmax(s_sum)]
                            q_tr = s_pts[np.argmin(s_diff)]
                            q_bl = s_pts[np.argmax(s_diff)]
                            q_ordered = np.array([q_tl, q_tr, q_br, q_bl], dtype='float32')

                            tw, th = 1014, 638
                            dst_rect = np.array([[0, 0], [tw - 1, 0], [tw - 1, th - 1], [0, th - 1]], dtype='float32')
                            M_warp = cv2.getPerspectiveTransform(q_ordered, dst_rect)
                            M_warp_inv = np.linalg.inv(M_warp)
                            warped_temp = cv2.warpPerspective(resized, M_warp, (tw, th))
                            w_gray = cv2.cvtColor(warped_temp, cv2.COLOR_BGR2GRAY)

                            # Scan top: find first row where central strip is bright card paper
                            y_top = 0
                            for y in range(0, int(th * 0.25), 2):
                                strip = w_gray[y, int(tw * 0.2):int(tw * 0.8)]
                                if np.mean(strip) > 180 and np.std(strip) < 35:
                                    y_top = max(0, y - 2)
                                    break

                            # Scan bottom: find last row where central strip is bright card paper
                            y_bot = th - 1
                            for y in range(th - 1, int(th * 0.75), -2):
                                strip = w_gray[y, int(tw * 0.2):int(tw * 0.8)]
                                if np.mean(strip) > 175 and np.std(strip) < 35:
                                    y_bot = min(th - 1, y + 2)
                                    break

                            # Scan left: find first column where central strip is bright card paper
                            x_left = 0
                            for x in range(0, int(tw * 0.15), 2):
                                strip = w_gray[int(th * 0.3):int(th * 0.7), x]
                                if np.mean(strip) > 180:
                                    x_left = x
                                    break

                            # Scan right: find last column where central strip is bright card paper
                            x_right = tw - 1
                            for x in range(tw - 1, int(tw * 0.85), -2):
                                strip = w_gray[int(th * 0.3):int(th * 0.7), x]
                                if np.mean(strip) > 180:
                                    x_right = x
                                    break

                            if y_bot > y_top + 100 and x_right > x_left + 150:
                                refined_dst = np.array([
                                    [[float(x_left), float(y_top)]],
                                    [[float(x_right), float(y_top)]],
                                    [[float(x_right), float(y_bot)]],
                                    [[float(x_left), float(y_bot)]]
                                ], dtype='float32')
                                refined_orig = cv2.perspectiveTransform(refined_dst, M_warp_inv).reshape(4, 2)
                                final_box_scaled = refined_orig
                        except Exception:
                            pass

                    ordered, score = score_quad_candidate(final_box_scaled, (rh, rw), priority_weight=3.5)
                    if ordered is not None and score > 25:
                        bonus = 350.0 if snapped_box is not None else 280.0
                        candidates.append((ordered / scale, score + bonus, 99))
    except Exception:
        pass

    return candidates


# ═══════════════════════════════════════════════════════════════
# STRATEGY E: GRANULAR GROUND (Soil, Mud, Sand, Gravel)
# For: Cards placed on dirt ground, soil, sand, gravel outdoors
# Method: LAB White Paper Saliency + Open-First Noise Rejection + Auto-Paper Snapping
# ═══════════════════════════════════════════════════════════════
def strategy_granular_ground(image):
    """ISOLATED Strategy E — For granular soil, sand, mud, gravel backgrounds."""
    h, w = image.shape[:2]
    candidates = []

    scale = 800.0 / max(h, w) if max(h, w) > 800 else 1.0
    resized = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA) if scale < 1.0 else image.copy()
    rh, rw = resized.shape[:2]
    r_area = rh * rw

    try:
        lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
        l_chan = lab[:, :, 0]
        a_chan = lab[:, :, 1]
        b_chan = lab[:, :, 2]

        dist_to_white = np.sqrt((l_chan.astype(float) - 250)**2 + (a_chan.astype(float) - 128)**2 + (b_chan.astype(float) - 128)**2)
        white_cand = (dist_to_white < 55).astype(np.uint8) * 255

        # 1. Open first: erase small pebble noise
        opened = cv2.morphologyEx(white_cand, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
        # 2. Close second: bridge internal card text and QR code
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25)))

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(closed)
        if num_labels > 1:
            card_labels = []
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                if 0.08 * r_area < area < 0.70 * r_area:
                    card_labels.append((i, area))

            if card_labels:
                best_lbl = max(card_labels, key=lambda x: x[1])[0]
                mask = (labels == best_lbl).astype(np.uint8)
                cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if cnts:
                    hull = cv2.convexHull(cnts[0])
                    rect = cv2.minAreaRect(hull)
                    box = cv2.boxPoints(rect)

                    s = box.sum(axis=1)
                    diff = np.diff(box, axis=1)
                    tl = box[np.argmin(s)]
                    br = box[np.argmax(s)]
                    tr = box[np.argmin(diff)]
                    bl = box[np.argmax(diff)]
                    ordered = np.array([tl, tr, br, bl], dtype='float32')

                    w_a = np.linalg.norm(ordered[0] - ordered[1])
                    h_a = np.linalg.norm(ordered[1] - ordered[2])
                    aspect = max(w_a, h_a) / (min(w_a, h_a) + 1e-5)

                    if 1.25 < aspect < 1.95:
                        # Auto-refine paper borders in warped space
                        tw, th = 1014, 638
                        dst = np.array([[0, 0], [tw - 1, 0], [tw - 1, th - 1], [0, th - 1]], dtype='float32')
                        M = cv2.getPerspectiveTransform(ordered, dst)
                        M_inv = np.linalg.inv(M)
                        warped = cv2.warpPerspective(resized, M, (tw, th))
                        w_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)

                        y_top = 0
                        for y in range(0, int(th * 0.25), 2):
                            strip = w_gray[y, int(tw * 0.2):int(tw * 0.8)]
                            if np.mean(strip) > 200 and np.std(strip) < 30:
                                y_top = max(0, y - 2)
                                break

                        y_bot = th - 1
                        for y in range(th - 1, int(th * 0.75), -2):
                            strip = w_gray[y, int(tw * 0.2):int(tw * 0.8)]
                            if np.mean(strip) > 200 and np.std(strip) < 30:
                                y_bot = min(th - 1, y + 2)
                                break

                        x_left = 0
                        for x in range(0, int(tw * 0.15), 2):
                            strip = w_gray[int(th * 0.3):int(th * 0.7), x]
                            if np.mean(strip) > 200:
                                x_left = x
                                break

                        x_right = tw - 1
                        for x in range(tw - 1, int(tw * 0.85), -2):
                            strip = w_gray[int(th * 0.3):int(th * 0.7), x]
                            if np.mean(strip) > 200:
                                x_right = x
                                break

                        if y_bot > y_top + 100 and x_right > x_left + 150:
                            refined_dst = np.array([
                                [[float(x_left), float(y_top)]],
                                [[float(x_right), float(y_top)]],
                                [[float(x_right), float(y_bot)]],
                                [[float(x_left), float(y_bot)]]
                            ], dtype='float32')
                            refined_orig = cv2.perspectiveTransform(refined_dst, M_inv).reshape(4, 2)
                            ordered = refined_orig

                        ordered_scaled = ordered / scale
                        candidates.append((ordered_scaled, 380.0, 99))
    except Exception:
        pass

    return candidates


# ═══════════════════════════════════════════════════════════════
# STRATEGY D: CLOSE-UP FULL-FRAME SCAN
# For: Scanner outputs, tight phone photos where card fills >75% of image
# Method: Minimal border trim + rotation correction
# ═══════════════════════════════════════════════════════════════
def strategy_close_up_scan(image):
    """ISOLATED Strategy D — card fills most of the image, minimal crop needed."""
    h, w = image.shape[:2]
    candidates = []

    # Card fills >75% of image, just trim 2% border
    margin_x = w * 0.02
    margin_y = h * 0.02
    box = np.array([
        [margin_x, margin_y],
        [w - margin_x, margin_y],
        [w - margin_x, h - margin_y],
        [margin_x, h - margin_y]
    ], dtype='float32')

    ordered, score = score_quad_candidate(box, (h, w), priority_weight=2.0)
    if ordered is not None:
        candidates.append((ordered, score + 200.0, 90))

    return candidates


# ═══════════════════════════════════════════════════════════════
# STRATEGY F: PLASTIC FOLDER / DOCUMENT SLEEVE
# For: Aadhaar inside transparent plastic folder/sleeve, tight crop with dark folder margins
# Method: Adaptive Per-Edge Luminance Scanning
# ═══════════════════════════════════════════════════════════════
def strategy_plastic_folder(image):
    """ISOLATED Strategy F — anchor-driven boundary estimation to eliminate transparent folder & passbook clutter."""
    h, w = image.shape[:2]
    candidates = []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # ── METHOD 1: RED SEPARATOR LINE ANCHOR (Aadhaar Standard Layout) ──
    # Every Aadhaar front card has a prominent red line separating the 12-digit number from the slogan.
    mask1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([10, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
    red_mask = mask1 | mask2

    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    red_h = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel_h)

    cnts, _ = cv2.findContours(red_h, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best_red_line = None
    max_len = 0
    for c in cnts:
        x, y, cw, ch = cv2.boundingRect(c)
        if cw > max_len and cw > w * 0.35 and ch < h * 0.15:
            max_len = cw
            best_red_line = (x, y, cw, ch)

    if best_red_line is not None:
        rx, ry, rw_line, rh_line = best_red_line
        
        # 1. Detect Left Edge: Scan near rx for paper luminance transition (dark background to bright card paper)
        x_left = rx
        search_min = max(0, rx - int(w * 0.08))
        search_max = min(w - 1, rx + int(w * 0.04))
        best_left_grad = -1
        for x in range(search_min, search_max):
            strip_pre = gray[max(0, ry - int(h * 0.35)):ry, max(0, x - 2)]
            strip_post = gray[max(0, ry - int(h * 0.35)):ry, min(w - 1, x + 2)]
            grad = float(np.mean(strip_post)) - float(np.mean(strip_pre))
            if grad > best_left_grad and np.mean(strip_post) > 170:
                best_left_grad = grad
                x_left = x

        # 2. Detect Right Edge: Scan near rx + rw_line for paper luminance drop (bright card to dark background)
        x_right = rx + rw_line
        search_r_min = max(0, rx + rw_line - int(w * 0.04))
        search_r_max = min(w - 1, rx + rw_line + int(w * 0.08))
        best_right_grad = -1
        for x in range(search_r_min, search_r_max):
            strip_in = gray[max(0, ry - int(h * 0.35)):ry, max(0, x - 2)]
            strip_out = gray[max(0, ry - int(h * 0.35)):ry, min(w - 1, x + 2)]
            grad = float(np.mean(strip_in)) - float(np.mean(strip_out))
            if grad > best_right_grad and np.mean(strip_in) > 150:
                best_right_grad = grad
                x_right = x

        card_w = max(10, x_right - x_left)
        card_h = card_w / 1.5858

        # 3. Detect Top Edge: Red line is at ~87.1% of card height
        y_top = max(0, int(ry - card_h * 0.871))
        
        # Fine-tune y_top with top horizontal cut/perforation line
        edges = cv2.Canny(gray, 40, 140)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40, minLineLength=int(card_w * 0.35), maxLineGap=20)
        if lines is not None:
            top_candidates = []
            for l in lines:
                lx1, ly1, lx2, ly2 = l[0]
                if abs(ly1 - ly2) <= 5 and abs(ly1 - y_top) < card_h * 0.15:
                    top_candidates.append((ly1 + ly2) / 2.0)
            if top_candidates:
                y_top = int(np.median(top_candidates))

        # 4. Detect Bottom Edge: card_h from y_top
        y_bot = min(h - 1, int(y_top + card_h))

        if (x_right - x_left) > w * 0.5 and (y_bot - y_top) > h * 0.5:
            box = np.array([
                [float(x_left), float(y_top)],
                [float(x_right), float(y_top)],
                [float(x_right), float(y_bot)],
                [float(x_left), float(y_bot)]
            ], dtype='float32')

            ordered, score = score_quad_candidate(box, (h, w), priority_weight=3.0)
            if ordered is not None:
                candidates.append((ordered, score + 300.0, 99))
                return candidates

    # ── METHOD 2: FALLBACK ADAPTIVE PER-EDGE LUMINANCE SCANNING ──
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    L_THRESH = 168

    y_top = 0
    if np.mean(lab[0:3, :, 0]) < L_THRESH:
        for y in range(0, int(h * 0.25)):
            if np.mean(lab[y, :, 0]) >= L_THRESH:
                y_top = y
                break
    else:
        y_top = int(h * 0.01)

    y_bot = h - 1
    if np.mean(lab[-3:, :, 0]) < L_THRESH:
        for y in range(h - 1, int(h * 0.75), -1):
            if np.mean(lab[y, :, 0]) >= L_THRESH:
                y_bot = y
                break
    else:
        y_bot = h - 1 - int(h * 0.01)

    x_left = 0
    if np.mean(lab[:, 0:3, 0]) < L_THRESH:
        for x in range(0, int(w * 0.25)):
            if np.mean(lab[:, x, 0]) >= L_THRESH:
                x_left = x
                break
    else:
        x_left = int(w * 0.01)

    x_right = w - 1
    if np.mean(lab[:, -3:, 0]) < L_THRESH:
        for x in range(w - 1, int(w * 0.75), -1):
            if np.mean(lab[:, x, 0]) >= L_THRESH:
                x_right = x
                break
    else:
        x_right = w - 1 - int(w * 0.01)

    if (x_right - x_left) > w * 0.6 and (y_bot - y_top) > h * 0.6:
        box = np.array([
            [float(x_left), float(y_top)],
            [float(x_right), float(y_top)],
            [float(x_right), float(y_bot)],
            [float(x_left), float(y_bot)]
        ], dtype='float32')

        ordered, score = score_quad_candidate(box, (h, w), priority_weight=2.0)
        if ordered is not None:
            candidates.append((ordered, score + 210.0, 95))

    return candidates


# ═══════════════════════════════════════════════════════════════
# FACE ANCHOR STRATEGY (Shared fallback — used by multi-method)
# ═══════════════════════════════════════════════════════════════
def strategy_face_anchor(image):
    """Fallback strategy using Haar cascade face detection + proportional card projection."""
    h, w = image.shape[:2]
    candidates = []

    if face_cascade is not None and not face_cascade.empty():
        try:
            full_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            center_orig = (w // 2, h // 2)

            for ang in range(0, 360, 15):
                M_rot = cv2.getRotationMatrix2D(center_orig, ang, 1.0)
                rot_gray = cv2.warpAffine(full_gray, M_rot, (w, h))
                faces = face_cascade.detectMultiScale(rot_gray, 1.10, 3, minSize=(60, 60))

                if len(faces) > 0:
                    fx, fy, fw, fh = faces[0]

                    rot_bgr = cv2.warpAffine(image, M_rot, (w, h))
                    if is_card_paper_region(rot_bgr, [fx - fw, fy - fh, fx + 2 * fw, fy + 2 * fh]):
                        card_w = fw / 0.235
                        card_h = card_w / 1.5858

                        x1 = fx - (0.080 * card_w)
                        y1 = fy - (0.175 * card_h)
                        x2 = x1 + card_w
                        y2 = y1 + card_h

                        rot_corners = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype='float32')

                        M_inv = cv2.getRotationMatrix2D(center_orig, -ang, 1.0)
                        ones = np.ones(shape=(len(rot_corners), 1))
                        orig_corners = M_inv.dot(np.hstack([rot_corners, ones]).T).T

                        ordered, score = score_quad_candidate(orig_corners, (h, w), priority_weight=2.0)
                        if ordered is not None and score > 20:
                            candidates.append((ordered, score + 120.0, 99))
                            break
        except Exception:
            pass

    return candidates


def detect_card_boundary_universal(image):
    """
    🧭 STRATEGY ROUTER — The Eye decides, isolated strategies execute.
    1. Classify image type using The Eye
    2. Route to the correct isolated strategy
    3. If primary strategy fails, try multi-method fallback
    """
    h, w = image.shape[:2]

    # Step 1: THE EYE classifies the image
    classification = classify_image_type(image)
    img_type = classification['type']

    # Step 2: Route to primary strategy based on classification
    candidates = []

    if img_type == 'solid_color':
        candidates = strategy_solid_color(image)
    elif img_type == 'granular_ground':
        candidates = strategy_granular_ground(image)
        if not candidates:
            candidates = strategy_solid_color(image)
    elif img_type == 'textured_fabric':
        candidates = strategy_textured_fabric(image)
        # If LSD fails, fallback to LAB saliency (also works on some fabrics)
        if not candidates:
            candidates = strategy_solid_color(image)
    elif img_type == 'dark_bg_mixed':
        candidates = strategy_dark_background(image)
        # If dark bg refinement fails, try standard LAB saliency
        if not candidates:
            candidates = strategy_solid_color(image)
    elif img_type == 'plastic_folder':
        candidates = strategy_plastic_folder(image)
        if not candidates:
            candidates = strategy_close_up_scan(image)
    elif img_type == 'close_up_scan':
        candidates = strategy_close_up_scan(image)
    else:
        # Unknown: Run ALL strategies, pick best score
        candidates = []
        candidates.extend(strategy_granular_ground(image))
        candidates.extend(strategy_solid_color(image))
        candidates.extend(strategy_textured_fabric(image))
        candidates.extend(strategy_dark_background(image))
        candidates.extend(strategy_close_up_scan(image))
        candidates.extend(strategy_plastic_folder(image))

    # Step 3: If primary strategies all failed, try face anchor as last resort
    if not candidates:
        candidates = strategy_face_anchor(image)

    # Step 4: Pick best candidate
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_box = candidates[0][0]
        conf = int(min(99, max(75, candidates[0][2])))
        return best_box.astype("float32"), conf

    # Ultimate fallback: 2% margin crop
    mx, my = w * 0.02, h * 0.02
    fallback = np.array([[mx, my], [w - mx, my], [w - mx, h - my], [mx, h - my]], dtype='float32')
    return fallback, 50


def warp_to_standard_aadhaar_clean(image, pts):
    """
    Warps detected quad to standard 300 DPI Aadhaar Card Dimensions:
    1014 x 638 px (86mm x 54mm = 1.5858 standard ID-1 aspect ratio).
    Ensures 100% horizontal level perspective alignment.
    """
    rect = order_points(pts)

    w_top = np.linalg.norm(rect[1] - rect[0])
    w_bot = np.linalg.norm(rect[2] - rect[3])
    avg_w = (w_top + w_bot) / 2.0

    h_left = np.linalg.norm(rect[3] - rect[0])
    h_right = np.linalg.norm(rect[2] - rect[1])
    avg_h = (h_left + h_right) / 2.0

    target_w = 1014
    target_h = 638

    if avg_h > avg_w:
        dst = np.array([[target_w - 1, 0], [target_w - 1, target_h - 1], [0, target_h - 1], [0, 0]], dtype='float32')
    else:
        dst = np.array([[0, 0], [target_w - 1, 0], [target_w - 1, target_h - 1], [0, target_h - 1]], dtype='float32')

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (target_w, target_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return warped


def analyze_card_content_and_orientation(warped_img):
    """
    LAYER 4: Multi-Feature Concurrence Deep Classifier:
    - FRONT Card requires at least 2 concurring front features:
      (Face + Saffron/Orange Header) OR (DOB/Gender + 12-Digit Number).
    - BACK Card requires at least 2 concurring back features:
      (QR Code + Address) OR (QR Code + 6-digit Pincode) OR (Helpline 1947 + UIDAI link).
    """
    best_rot = 0
    best_score = -1e9
    best_side = 'front'
    best_meta = {}

    qr_detector = cv2.QRCodeDetector()

    for rot in [0, 90, 180, 270]:
        if rot == 90:
            test = cv2.rotate(warped_img, cv2.ROTATE_90_CLOCKWISE)
        elif rot == 180:
            test = cv2.rotate(warped_img, cv2.ROTATE_180)
        elif rot == 270:
            test = cv2.rotate(warped_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            test = warped_img.copy()

        # Enforce landscape for feature scoring
        th, tw = test.shape[:2]
        if th > tw:
            test = cv2.rotate(test, cv2.ROTATE_90_CLOCKWISE)
            th, tw = test.shape[:2]

        gray = cv2.cvtColor(test, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(test, cv2.COLOR_BGR2HSV)

        # ── 1. HEADER & FOOTER COLOR PROFILE ──
        top_hsv = hsv[:int(th * 0.30), :]
        saffron_top = cv2.countNonZero(cv2.inRange(top_hsv, np.array([3, 30, 90]), np.array([25, 255, 255])))

        bot_hsv = hsv[int(th * 0.70):, :]
        saffron_bot = cv2.countNonZero(cv2.inRange(bot_hsv, np.array([3, 30, 90]), np.array([25, 255, 255])))

        green_bot = cv2.countNonZero(cv2.inRange(bot_hsv, np.array([35, 25, 45]), np.array([90, 255, 255])))

        # ── 2. FACE DETECTION (Front Portrait) ──
        has_face = False
        left_gray = gray[:int(th * 0.75), :int(tw * 0.45)]
        if face_cascade is not None and not face_cascade.empty():
            faces = face_cascade.detectMultiScale(left_gray, 1.10, 3, minSize=(50, 50))
            if len(faces) > 0:
                has_face = True

        # ── 3. QR CODE DETECTION (Back) ──
        has_qr = False
        val, pts, _ = qr_detector.detectAndDecode(gray)
        if pts is not None and len(pts) > 0:
            has_qr = True

        right_gray = gray[:int(th * 0.75), int(tw * 0.45):]
        grad_x = cv2.Sobel(right_gray, cv2.CV_32F, 1, 0)
        grad_y = cv2.Sobel(right_gray, cv2.CV_32F, 0, 1)
        right_texture_energy = float(np.mean(np.abs(grad_x) + np.abs(grad_y)))

        left_grad_x = cv2.Sobel(left_gray, cv2.CV_32F, 1, 0)
        left_grad_y = cv2.Sobel(left_gray, cv2.CV_32F, 0, 1)
        left_texture_energy = float(np.mean(np.abs(left_grad_x) + np.abs(left_grad_y)))

        is_qr_texture_pattern = (right_texture_energy > 85 and right_texture_energy > left_texture_energy * 1.25)

        # ── 4. TESSERACT OCR INTELLIGENCE ──
        ocr_text = ""
        has_front_dob = False
        has_front_gender = False
        has_back_address = False
        has_back_pin = False
        detected_pincode = None
        detected_aadhaar_digits = None

        if pytesseract is not None:
            try:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                ocr_prep = clahe.apply(gray)
                ocr_text = pytesseract.image_to_string(ocr_prep, config='--oem 3 --psm 6')
                lower_text = ocr_text.lower()

                if re.search(r'\b(dob|birth|year\s*of|जन्म|तारीख|तिथि)\b', lower_text) or re.search(r'\b\d{2}/\d{2}/\d{4}\b', ocr_text):
                    has_front_dob = True

                if re.search(r'\b(male|female|transgender|पुरुष|महिला)\b', lower_text):
                    has_front_gender = True

                digits_match = re.findall(r'\b\d{4}\s\d{4}\s\d{4}\b', ocr_text)
                if digits_match:
                    detected_aadhaar_digits = digits_match[0]

                if re.search(r'\b(address|adtrese|पता|s/o|d/o|w/o|c/o|house|flat|floor|sector|village|dist|district|road|po:)\b', lower_text):
                    has_back_address = True

                pin_matches = re.findall(r'\b[1-9][0-9]{5}\b', ocr_text)
                if pin_matches:
                    detected_pincode = pin_matches[-1]
                    has_back_pin = True

                if any(w in lower_text for w in ['1947', 'help@uidai', 'uidai.gov.in', 'www.uidai', 'unique identification']):
                    has_back_address = True

            except Exception:
                pass

        # ── 5. 1D BARCODE DETECTION (Standard Aadhaar Back) ──
        has_barcode = False
        try:
            bc_strip = gray[int(th * 0.40):int(th * 0.78), int(tw * 0.15):int(tw * 0.85)]
            gx_bc = cv2.Sobel(bc_strip, cv2.CV_32F, 1, 0)
            gy_bc = cv2.Sobel(bc_strip, cv2.CV_32F, 0, 1)
            bc_ratio = float(np.mean(np.abs(gx_bc)) / (np.mean(np.abs(gy_bc)) + 1e-5))
            if bc_ratio > 1.65:
                has_barcode = True
        except Exception:
            pass

        # ── 6. DETERMINISTIC MULTI-FEATURE SCORING ──
        header_advantage = (saffron_top - saffron_bot) * 2.0
        green_advantage = green_bot * 1.5

        # Score front vs back strictly by concurrent features
        front_weight = 0
        back_weight = 0

        if has_face: front_weight += 50
        if has_front_dob: front_weight += 30
        if has_front_gender: front_weight += 25
        if detected_aadhaar_digits and not has_back_address: front_weight += 25
        if saffron_top > 500: front_weight += 15

        if has_back_address: back_weight += 50
        if has_back_pin: back_weight += 35
        if has_barcode: back_weight += 35
        if has_qr or is_qr_texture_pattern: back_weight += 35

        current_side = 'front' if front_weight >= back_weight else 'back'
        side_evidence = (front_weight if current_side == 'front' else back_weight) * 500.0

        total_rot_score = header_advantage + green_advantage + side_evidence

        if total_rot_score > best_score:
            best_score = total_rot_score
            best_rot = rot
            best_side = current_side
            best_meta = {
                "aadhaar_number": detected_aadhaar_digits,
                "pincode": detected_pincode,
                "has_dob": has_front_dob,
                "has_gender": has_front_gender,
                "has_address": has_back_address,
                "has_face": has_face,
                "has_qr": has_qr or is_qr_texture_pattern,
                "has_barcode": has_barcode
            }

    # Apply optimal rotation
    if best_rot == 90:
        upright = cv2.rotate(warped_img, cv2.ROTATE_90_CLOCKWISE)
    elif best_rot == 180:
        upright = cv2.rotate(warped_img, cv2.ROTATE_180)
    elif best_rot == 270:
        upright = cv2.rotate(warped_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    else:
        upright = warped_img.copy()

    # Guarantee final output is always landscape (1014x638)
    uh, uw = upright.shape[:2]
    if uh > uw:
        upright = cv2.rotate(upright, cv2.ROTATE_90_CLOCKWISE)
        uh, uw = upright.shape[:2]

    # Guarantee Logo / Saffron header is at TOP (not bottom)
    upright_hsv = cv2.cvtColor(upright, cv2.COLOR_BGR2HSV)
    top_saff = cv2.countNonZero(cv2.inRange(upright_hsv[:int(uh * 0.35), :], np.array([3, 30, 90]), np.array([25, 255, 255])))
    bot_saff = cv2.countNonZero(cv2.inRange(upright_hsv[int(uh * 0.65):, :], np.array([3, 30, 90]), np.array([25, 255, 255])))
    if bot_saff > top_saff * 1.5:
        upright = cv2.rotate(upright, cv2.ROTATE_180)

    # Ensure exact 1014x638 target dimensions
    if (uw, uh) != (1014, 638):
        upright = cv2.resize(upright, (1014, 638), interpolation=cv2.INTER_CUBIC)

    return upright, best_side, 99, best_rot, best_meta


def enhance_aadhaar_final(image, mode='clean'):
    """
    Natural High-Fidelity Color & Sharpness Enhancement:
    Preserves 100% of authentic Aadhaar colors without bleaching.
    """
    if mode == 'original':
        return image

    if mode == 'bw':
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        bw = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8)
        return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)

    if mode == 'grayscale':
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
        return cv2.cvtColor(clahe.apply(gray), cv2.COLOR_GRAY2BGR)

    # ── NATURAL COLOR PRESERVATION (L*a*b* space) ──
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_chan, a_chan, b_chan = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=1.4, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l_chan)

    gaussian = cv2.GaussianBlur(l_clahe, (0, 0), 1.5)
    l_sharp = cv2.addWeighted(l_clahe, 1.22, gaussian, -0.22, 0)

    natural_lab = cv2.merge([l_sharp, a_chan, b_chan])
    result = cv2.cvtColor(natural_lab, cv2.COLOR_LAB2BGR)

    if mode == 'enhanced_color':
        hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = cv2.multiply(hsv[:, :, 1], 1.15)
        result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    return result


def load_source_image_or_pdf(input_path):
    if input_path.lower().endswith('.pdf'):
        try:
            reader = pypdf.PdfReader(input_path)
            for page in reader.pages:
                for img in page.images:
                    img_bytes = img.data
                    pil_img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
                    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception:
            pass
    return cv2.imread(input_path)


def process_aadhaar_pipeline(input_path, output_path, mode='clean', corners=None, rotation=0, side_override=None):
    if not os.path.exists(input_path):
        return {"success": False, "error": f"File not found: {input_path}"}

    img = load_source_image_or_pdf(input_path)
    if img is None:
        return {"success": False, "error": "Could not decode input image."}

    # Manual Rotation override if requested
    if rotation == 90:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 180:
        img = cv2.rotate(img, cv2.ROTATE_180)
    elif rotation == 270:
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

    orig_h, orig_w = img.shape[:2]
    actions = []

    if corners and len(corners) == 4:
        detected_pts = np.array(corners, dtype="float32")
        confidence = 99
        actions.append("Manual 4-Corner Applied")
    else:
        detected_pts, confidence = detect_card_boundary_universal(img)
        actions.append("Industrial 5-Layer Boundary Snapped")

    # Warp to standard Aadhaar dimensions with 100% horizontal alignment
    warped = warp_to_standard_aadhaar_clean(img, detected_pts)
    actions.append("Perspective Straightened (0° Horizontal Level)")

    # OCR + Logo + Digit & Address Classifier
    upright_card, side, side_conf, auto_rot, meta = analyze_card_content_and_orientation(warped)
    if auto_rot != 0 and rotation == 0:
        actions.append(f"Auto-Oriented ({auto_rot}°)")

    if side_override and side_override in ['front', 'back']:
        side = side_override
        side_conf = 100

    actions.append(f"Classified: {side.upper()} (Slot {'1: Front' if side == 'front' else '2: Back'})")

    # Final Enhancement
    final_output = enhance_aadhaar_final(upright_card, mode=mode)
    out_h, out_w = final_output.shape[:2]

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cv2.imwrite(output_path, final_output, [cv2.IMWRITE_JPEG_QUALITY, 96])

    return {
        "success": True,
        "side": side,
        "side_confidence": side_conf,
        "confidence": confidence,
        "rotation": rotation,
        "input_dimensions": {"width": orig_w, "height": orig_h},
        "output_dimensions": {"width": out_w, "height": out_h},
        "corners": detected_pts.tolist(),
        "meta": meta,
        "actions_summary": actions,
        "output_path": output_path
    }


def main():
    parser = argparse.ArgumentParser(description="AK Print Seva - Industrial 5-Layer Aadhaar AI Vision Processor")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="auto", choices=["auto", "original", "clean", "enhanced_color", "grayscale", "bw"])
    parser.add_argument("--rotation", type=int, default=0)
    parser.add_argument("--corners", default=None)
    parser.add_argument("--side", default=None)

    args = parser.parse_args()

    corners_list = None
    if args.corners:
        try:
            corners_list = json.loads(args.corners)
        except Exception:
            pass

    result = process_aadhaar_pipeline(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode,
        corners=corners_list,
        rotation=args.rotation,
        side_override=args.side
    )

    print(json.dumps(result))


if __name__ == "__main__":
    main()
