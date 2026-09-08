"""
═══════════════════════════════════════════════════════════════
AK PRINT SEVA — AI Document Processing & Computer Vision Engine
services/document-ai/doc_processor.py
═══════════════════════════════════════════════════════════════
"""

import sys
import os
import json
import argparse
import math
import numpy as np
import cv2
from PIL import Image

def order_points(pts):
    """
    Orders 4 points in order: top-left, top-right, bottom-right, bottom-left.
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # Top-left has smallest sum
    rect[2] = pts[np.argmax(s)]  # Bottom-right has largest sum

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # Top-right has smallest diff
    rect[3] = pts[np.argmax(diff)]  # Bottom-left has largest diff
    return rect

def detect_document_corners(image):
    """
    Universal Multi-Layer Document Corner Detector:
    1. True Otsu Threshold Contours (Geometric Quadrilaterals)
    2. Multi-Scale Canny Edge Contours
    3. Adaptive Lightness / LAB Segmentation
    4. Text & Content Density Quadrilateral
    Handles documents on tables, bedsheets, floors, hands, textured desks, etc.
    """
    orig_h, orig_w = image.shape[:2]
    scale = 900.0 / max(orig_h, orig_w)
    resized = cv2.resize(image, (int(orig_w * scale), int(orig_h * scale)), interpolation=cv2.INTER_AREA) if scale < 1.0 else image.copy()
    rh, rw = resized.shape[:2]
    r_area = rh * rw

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.bilateralFilter(gray, 9, 75, 75)

    candidates = []

    # Strategy 1: Otsu Threshold Contours (Geometric Quadrilaterals)
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    for mask in [otsu, 255 - otsu]:
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            area = cv2.contourArea(c)
            if 0.15 * r_area < area < 0.96 * r_area:
                hull = cv2.convexHull(c)
                approx = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True)
                if len(approx) == 4:
                    pts = approx.reshape(4, 2)
                    x, y, bw, bh = cv2.boundingRect(hull)
                    solidity = area / (bw * bh) if (bw * bh) > 0 else 0
                    if solidity > 0.65:
                        score = area * (solidity ** 2) * 3.2
                        candidates.append((pts, score, 98))

    # Strategy 2: Multi-Scale Canny Edges
    edged = cv2.Canny(blurred, 30, 120)
    kernel_e = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edged = cv2.dilate(edged, kernel_e, iterations=1)
    cnts_e, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts_e:
        area = cv2.contourArea(c)
        if 0.15 * r_area < area < 0.96 * r_area:
            hull = cv2.convexHull(c)
            approx = cv2.approxPolyDP(hull, 0.025 * cv2.arcLength(hull, True), True)
            if len(approx) == 4:
                pts = approx.reshape(4, 2)
                x, y, bw, bh = cv2.boundingRect(hull)
                solidity = area / (bw * bh) if (bw * bh) > 0 else 0
                if solidity > 0.65:
                    candidates.append((pts, area * solidity * 2.5, 95))

    # Strategy 3: Adaptive LAB Lightness Segmentation
    lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0]
    l_thresh = cv2.adaptiveThreshold(l_channel, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5)
    cnts_l, _ = cv2.findContours(l_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts_l:
        area = cv2.contourArea(c)
        if 0.20 * r_area < area < 0.95 * r_area:
            hull = cv2.convexHull(c)
            approx = cv2.approxPolyDP(hull, 0.03 * cv2.arcLength(hull, True), True)
            if len(approx) == 4:
                pts = approx.reshape(4, 2)
                candidates.append((pts, area * 1.8, 90))

    # Strategy 4: Salient Text/Content Bounding Density Hull
    thresh_t = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 6)
    margin_x = int(rw * 0.03)
    margin_y = int(rh * 0.03)
    thresh_t[:, :margin_x] = 0
    thresh_t[:, rw-margin_x:] = 0
    thresh_t[:margin_y, :] = 0
    thresh_t[rh-margin_y:, :] = 0
    dilated = cv2.dilate(thresh_t, cv2.getStructuringElement(cv2.MORPH_RECT, (int(rw*0.04), int(rh*0.03))), iterations=2)
    cnts_t, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if cnts_t:
        largest_t = max(cnts_t, key=cv2.contourArea)
        area_t = cv2.contourArea(largest_t)
        if area_t > 0.12 * r_area:
            tx, ty, tbw, tbh = cv2.boundingRect(largest_t)
            pad_x = int(tbw * 0.04)
            pad_y = int(tbh * 0.04)
            poly_t = np.array([
                [max(int(rw*0.015), tx - pad_x), max(int(rh*0.015), ty - pad_y)],
                [min(rw - int(rw*0.015), tx + tbw + pad_x), max(int(rh*0.015), ty - pad_y)],
                [min(rw - int(rw*0.015), tx + tbw + pad_x), min(rh - int(rh*0.015), ty + tbh + pad_y)],
                [max(int(rw*0.015), tx - pad_x), min(rh - int(rh*0.015), ty + tbh + pad_y)]
            ], dtype='float32')
            candidates.append((poly_t, area_t * 0.9, 85))

    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_pts = candidates[0][0] / scale
        return order_points(best_pts), candidates[0][2]

    # Safe Fallback with 2.5% safe margin
    mx, my = orig_w * 0.025, orig_h * 0.025
    fallback_pts = np.array([
        [mx, my],
        [orig_w - mx, my],
        [orig_w - mx, orig_h - my],
        [mx, orig_h - my]
    ], dtype='float32')
    return fallback_pts, 60

def four_point_transform(image, pts):
    """
    Performs perspective warp given 4 ordered points.
    """
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    # Width of new image
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    # Height of new image
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    if maxWidth < 50 or maxHeight < 50:
        return image

    # Destination points
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight), flags=cv2.INTER_CUBIC)
    return warped

def detect_and_deskew(image):
    """
    Calculates slight skew angle using Hough line transform and deskews image.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=image.shape[1] // 4, maxLineGap=20)
    
    if lines is None:
        return image, 0.0

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        if abs(angle) < 15.0:
            angles.append(angle)

    if not angles:
        return image, 0.0

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.25:
        return image, 0.0

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated, median_angle

def remove_shadows_and_normalize(image):
    """
    Estimates background illumination using morphological dilation and normalizes lighting.
    """
    rgb_planes = cv2.split(image)
    result_planes = []
    
    for plane in rgb_planes:
        dilated_img = cv2.dilate(plane, np.ones((7, 7), np.uint8))
        bg_img = cv2.medianBlur(dilated_img, 21)
        diff_img = 255 - cv2.absdiff(plane, bg_img)
        norm_img = cv2.normalize(diff_img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
        result_planes.append(norm_img)

    result = cv2.merge(result_planes)
    return result

def enhance_image(image, mode='auto'):
    """
    Applies image enhancement presets:
    - 'original': untouched colors
    - 'auto': balanced illumination and sharpness
    - 'clean': whitened background + dark text
    - 'enhanced_color': vibrant stamps/colors + white background
    - 'grayscale': smooth black and white tones
    - 'bw': crisp high-contrast binarized scan
    """
    if mode == 'original':
        return image

    if mode == 'grayscale':
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced_gray = clahe.apply(gray)
        return cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)

    if mode == 'bw':
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        bw = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8)
        return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)

    if mode in ['clean', 'auto', 'enhanced_color']:
        # Shadow reduction
        normalized = remove_shadows_and_normalize(image)

        # Unsharp masking for crisp text
        gaussian = cv2.GaussianBlur(normalized, (0, 0), 2.0)
        unsharp = cv2.addWeighted(normalized, 1.4, gaussian, -0.4, 0)

        if mode == 'clean':
            return cv2.convertScaleAbs(unsharp, alpha=1.15, beta=10)
        elif mode == 'enhanced_color':
            hsv = cv2.cvtColor(unsharp, cv2.COLOR_BGR2HSV)
            hsv[:, :, 1] = cv2.multiply(hsv[:, :, 1], 1.25)
            return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        else: # auto
            return unsharp

    return image

def check_image_quality(image):
    """
    Checks resolution and blur metric to provide user feedback.
    """
    h, w = image.shape[:2]
    is_low_res = (w < 600 or h < 600)
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    is_blurry = laplacian_var < 50.0

    warning = None
    if is_low_res or is_blurry:
        warning = "Image quality is low and may affect print clarity."

    return {
        "is_low_res": is_low_res,
        "is_blurry": is_blurry,
        "blur_score": round(float(laplacian_var), 2),
        "warning": warning
    }

def process_document(input_path, output_path, mode='auto', corners=None, rotation=0):
    """
    Main document processing execution pipeline.
    """
    if not os.path.exists(input_path):
        return {"success": False, "error": f"File not found: {input_path}"}

    img = cv2.imread(input_path)
    if img is None:
        return {"success": False, "error": "Invalid or unreadable image file"}

    orig_h, orig_w = img.shape[:2]
    quality_info = check_image_quality(img)

    actions_applied = []

    # 1. Manual or Auto Corners
    if corners is not None and len(corners) == 4:
        pts = np.array(corners, dtype="float32")
        confidence = 100
        actions_applied.append("Manual corners applied")
    else:
        pts, confidence = detect_document_corners(img)
        actions_applied.append("AI 4-corner boundary detected")

    # 2. Perspective Warp
    warped = four_point_transform(img, pts)
    actions_applied.append("Perspective corrected")

    # 3. User Rotation (0, 90, 180, 270)
    if rotation == 90:
        warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
        actions_applied.append("Rotated 90° CW")
    elif rotation == 180:
        warped = cv2.rotate(warped, cv2.ROTATE_180)
        actions_applied.append("Rotated 180°")
    elif rotation == 270:
        warped = cv2.rotate(warped, cv2.ROTATE_90_COUNTERCLOCKWISE)
        actions_applied.append("Rotated 270° CW")

    # 4. Deskew slight tilt
    deskewed, skew_angle = detect_and_deskew(warped)
    if abs(skew_angle) >= 0.25:
        actions_applied.append(f"Deskewed {skew_angle:.1f}°")

    # 5. Image Enhancement Preset
    enhanced = enhance_image(deskewed, mode=mode)
    if mode != 'original':
        actions_applied.append(f"Enhancement applied ({mode})")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 6. Save processed image
    cv2.imwrite(output_path, enhanced, [cv2.IMWRITE_JPEG_QUALITY, 95])

    proc_h, proc_w = enhanced.shape[:2]
    orientation = "landscape" if proc_w > proc_h else "portrait"
    actions_applied.append(f"A4 {orientation.capitalize()} ready")

    metrics = {
        "success": True,
        "input_dimensions": {"width": orig_w, "height": orig_h},
        "output_dimensions": {"width": proc_w, "height": proc_h},
        "detected_corners": pts.tolist(),
        "confidence": confidence,
        "skew_angle": round(skew_angle, 2),
        "rotation": rotation,
        "mode": mode,
        "orientation": orientation,
        "quality_warning": quality_info.get("warning"),
        "actions_summary": actions_applied,
        "output_path": output_path
    }
    return metrics

def main():
    parser = argparse.ArgumentParser(description="SMART A4 AI Document Processor")
    parser.add_argument("--input", required=True, help="Input image file path")
    parser.add_argument("--output", required=True, help="Output image file path")
    parser.add_argument("--mode", default="auto", choices=["auto", "clean", "enhanced_color", "grayscale", "bw", "original"], help="Enhancement preset")
    parser.add_argument("--corners", default=None, help="Optional JSON array of 4 corners: [[x,y],[x,y],[x,y],[x,y]]")
    parser.add_argument("--rotation", type=int, default=0, choices=[0, 90, 180, 270], help="Rotation angle in degrees")
    args = parser.parse_args()

    corners = None
    if args.corners:
        try:
            corners = json.loads(args.corners)
        except Exception:
            corners = None

    result = process_document(
        input_path=args.input,
        output_path=args.output,
        mode=args.mode,
        corners=corners,
        rotation=args.rotation
    )

    print(json.dumps(result))

if __name__ == "__main__":
    main()
