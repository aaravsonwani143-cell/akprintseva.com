"""
═══════════════════════════════════════════════════════════════
AK PRINT SEVA — Tool 1: Tedhi Medhi Image Scanner Engine
services/tedhi-medhi-ai/scanner_engine.py
Dedicated Computer Vision Perspective Straightener
═══════════════════════════════════════════════════════════════
"""

import sys
import os
import json
import argparse
import math
import numpy as np
import cv2

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def detect_corners(image):
    orig_h, orig_w = image.shape[:2]
    scale = 800.0 / max(orig_h, orig_w)
    resized = cv2.resize(image, (int(orig_w * scale), int(orig_h * scale)), interpolation=cv2.INTER_AREA) if scale < 1.0 else image.copy()
    rh, rw = resized.shape[:2]
    r_area = rh * rw

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.bilateralFilter(gray, 9, 75, 75)

    candidates = []

    # Otsu
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    for mask in [otsu, 255 - otsu]:
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            area = cv2.contourArea(c)
            if 0.15 * r_area < area < 0.95 * r_area:
                hull = cv2.convexHull(c)
                approx = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True)
                if len(approx) == 4:
                    pts = approx.reshape(4, 2)
                    x, y, bw, bh = cv2.boundingRect(hull)
                    solidity = area / (bw * bh) if (bw * bh) > 0 else 0
                    if solidity > 0.65:
                        candidates.append((pts, area * (solidity ** 2) * 3.0, 98))

    # Canny
    edged = cv2.Canny(blurred, 30, 110)
    cnts_e, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts_e:
        area = cv2.contourArea(c)
        if 0.15 * r_area < area < 0.95 * r_area:
            hull = cv2.convexHull(c)
            approx = cv2.approxPolyDP(hull, 0.025 * cv2.arcLength(hull, True), True)
            if len(approx) == 4:
                pts = approx.reshape(4, 2)
                x, y, bw, bh = cv2.boundingRect(hull)
                solidity = area / (bw * bh) if (bw * bh) > 0 else 0
                if solidity > 0.65:
                    candidates.append((pts, area * solidity * 2.2, 95))

    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_pts = candidates[0][0] / scale
        return order_points(best_pts), candidates[0][2]

    # Fallback
    mx, my = orig_w * 0.03, orig_h * 0.03
    return np.array([[mx, my], [orig_w - mx, my], [orig_w - mx, orig_h - my], [mx, orig_h - my]], dtype='float32'), 65

def four_point_transform(image, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    dst = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (maxWidth, maxHeight), flags=cv2.INTER_CUBIC)

def deskew(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=image.shape[1] // 4, maxLineGap=20)
    if lines is None:
        return image, 0.0
    angles = [math.degrees(math.atan2(l[0][3] - l[0][1], l[0][2] - l[0][0])) for l in lines if abs(math.degrees(math.atan2(l[0][3] - l[0][1], l[0][2] - l[0][0]))) < 15.0]
    if not angles:
        return image, 0.0
    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.25:
        return image, 0.0
    h, w = image.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), median_angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE), median_angle

def enhance(image, mode='auto'):
    if mode == 'original':
        return image
    if mode == 'bw':
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        bw = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8)
        return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
    if mode == 'grayscale':
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return cv2.cvtColor(clahe.apply(gray), cv2.COLOR_GRAY2BGR)
    
    # Shadow normalization
    rgb_planes = cv2.split(image)
    result_planes = []
    for plane in rgb_planes:
        dilated = cv2.dilate(plane, np.ones((7, 7), np.uint8))
        bg = cv2.medianBlur(dilated, 21)
        diff = 255 - cv2.absdiff(plane, bg)
        norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
        result_planes.append(norm)
    normalized = cv2.merge(result_planes)
    gaussian = cv2.GaussianBlur(normalized, (0, 0), 2.0)
    return cv2.addWeighted(normalized, 1.4, gaussian, -0.4, 0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="auto")
    parser.add_argument("--corners", default=None)
    parser.add_argument("--rotation", type=int, default=0)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(json.dumps({"success": False, "error": "Input file not found"}))
        return

    img = cv2.imread(args.input)
    if img is None:
        print(json.dumps({"success": False, "error": "Invalid image"}))
        return

    corners = json.loads(args.corners) if args.corners else None
    if corners and len(corners) == 4:
        pts = np.array(corners, dtype="float32")
        conf = 100
    else:
        pts, conf = detect_corners(img)

    warped = four_point_transform(img, pts)
    if args.rotation == 90:
        warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
    elif args.rotation == 180:
        warped = cv2.rotate(warped, cv2.ROTATE_180)
    elif args.rotation == 270:
        warped = cv2.rotate(warped, cv2.ROTATE_90_COUNTERCLOCKWISE)

    deskewed, skew_angle = deskew(warped)
    enhanced = enhance(deskewed, mode=args.mode)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    cv2.imwrite(args.output, enhanced, [cv2.IMWRITE_JPEG_QUALITY, 95])

    print(json.dumps({
        "success": True,
        "confidence": conf,
        "skew_angle": round(skew_angle, 2),
        "corners": pts.tolist(),
        "output_path": args.output
    }))

if __name__ == "__main__":
    main()
