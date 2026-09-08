#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
AK PRINT SEVA — CYBER CAFE SMART PDF PRINT QUEUE ENGINE
services/pdf/pdf_queue_processor.py
Direct Lossless Stream Merger, Orientation Preserver & A4 Normalizer (pypdf 6.16.2)
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
import json
import os
import io
import math
from typing import List, Dict, Any, Optional

try:
    import pypdf
    from pypdf import PdfReader, PdfWriter, Transformation
    from pypdf.generic import RectangleObject
except ImportError:
    print(json.dumps({
        "success": False,
        "error": "pypdf library not found. Please ensure pypdf is installed in Python environment."
    }))
    sys.exit(1)

# Standard A4 Dimensions in Points (72 points/inch: 210mm x 297mm)
A4_WIDTH_PT = 595.28
A4_HEIGHT_PT = 841.89
MM_TO_PT = 72.0 / 25.4


def analyze_pdf(file_path: str, password: Optional[str] = None) -> Dict[str, Any]:
    """Inspects a PDF file and returns page count, sizes, orientations, encryption status."""
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}

    try:
        reader = PdfReader(file_path)
        is_encrypted = reader.is_encrypted

        if is_encrypted:
            if password:
                decrypted = reader.decrypt(password)
                if decrypted == 0:
                    return {
                        "success": True,
                        "encrypted": True,
                        "password_required": True,
                        "password_valid": False,
                        "page_count": 0,
                        "pages": []
                    }
            else:
                return {
                    "success": True,
                    "encrypted": True,
                    "password_required": True,
                    "password_valid": False,
                    "page_count": 0,
                    "pages": []
                }

        page_count = len(reader.pages)
        pages_info = []
        has_mixed_sizes = False
        has_mixed_orientations = False
        first_box = None
        first_orient = None

        has_signature = False
        try:
            if reader.trailer and "/Root" in reader.trailer:
                catalog = reader.trailer["/Root"]
                if "/AcroForm" in catalog:
                    acro = catalog["/AcroForm"]
                    if "/SigFlags" in acro:
                        has_signature = True
        except Exception:
            pass

        for idx, page in enumerate(reader.pages):
            box = page.mediabox
            width_pt = float(box.width)
            height_pt = float(box.height)
            rotation = page.get("/Rotate", 0) or 0

            # Orientation
            effective_w = height_pt if rotation in (90, 270) else width_pt
            effective_h = width_pt if rotation in (90, 270) else height_pt
            is_landscape = effective_w > effective_h
            orientation_str = "Landscape" if is_landscape else "Portrait"

            width_mm = round(effective_w / MM_TO_PT, 1)
            height_mm = round(effective_h / MM_TO_PT, 1)

            if first_box is None:
                first_box = (round(width_mm), round(height_mm))
                first_orient = orientation_str
            else:
                if (round(width_mm), round(height_mm)) != first_box:
                    has_mixed_sizes = True
                if orientation_str != first_orient:
                    has_mixed_orientations = True

            pages_info.append({
                "page_number": idx + 1,
                "width_pt": width_pt,
                "height_pt": height_pt,
                "width_mm": width_mm,
                "height_mm": height_mm,
                "rotation": rotation,
                "orientation": orientation_str
            })

        return {
            "success": True,
            "encrypted": is_encrypted,
            "password_required": False,
            "password_valid": True if is_encrypted else None,
            "page_count": page_count,
            "pages": pages_info,
            "has_mixed_sizes": has_mixed_sizes,
            "has_mixed_orientations": has_mixed_orientations,
            "has_signature": has_signature
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to analyze PDF: {str(e)}"
        }


def merge_pdf_queue(job_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merges multiple PDFs in exact sequential order.
    Supports:
    - Zero page loss validation
    - Preserve original vs A4 normalization
    - Configurable safe margin in A4 mode
    - Output page mapping
    """
    files = job_config.get("files", [])
    output_path = job_config.get("output_path")
    mode = job_config.get("page_size_mode", "preserve_original")  # 'preserve_original' or 'normalize_a4'
    margin_mm = float(job_config.get("margin_mm", 5.0))

    if not files:
        return {"success": False, "error": "No files provided for merging."}
    if not output_path:
        return {"success": False, "error": "Output path not specified."}

    writer = PdfWriter()
    page_map = []
    total_expected_pages = 0
    total_output_pages = 0

    margin_pt = margin_mm * MM_TO_PT

    for file_entry in files:
        file_path = file_entry.get("path")
        file_id = file_entry.get("file_id", os.path.basename(file_path))
        file_name = file_entry.get("original_name", os.path.basename(file_path))
        password = file_entry.get("password")
        excluded_pages = set(file_entry.get("excluded_pages", []))

        if not os.path.exists(file_path):
            return {"success": False, "error": f"Source file missing: {file_name}"}

        reader = PdfReader(file_path)
        if reader.is_encrypted:
            if not password or reader.decrypt(password) == 0:
                return {"success": False, "error": f"PDF is password protected: {file_name}"}

        num_pages = len(reader.pages)

        for p_idx in range(num_pages):
            orig_page_num = p_idx + 1
            if orig_page_num in excluded_pages:
                continue

            total_expected_pages += 1
            source_page = reader.pages[p_idx]

            if mode == "normalize_a4":
                orig_box = source_page.mediabox
                orig_w = float(orig_box.width)
                orig_h = float(orig_box.height)
                rotation = source_page.get("/Rotate", 0) or 0

                is_landscape = (orig_h > orig_w) if rotation in (90, 270) else (orig_w > orig_h)

                target_w = A4_HEIGHT_PT if is_landscape else A4_WIDTH_PT
                target_h = A4_WIDTH_PT if is_landscape else A4_HEIGHT_PT

                printable_w = max(10.0, target_w - (2 * margin_pt))
                printable_h = max(10.0, target_h - (2 * margin_pt))

                scale = min(printable_w / orig_w, printable_h / orig_h)
                scaled_w = orig_w * scale
                scaled_h = orig_h * scale

                offset_x = (target_w - scaled_w) / 2.0
                offset_y = (target_h - scaled_h) / 2.0

                a4_page = writer.add_blank_page(width=target_w, height=target_h)
                transform = Transformation().scale(scale).translate(offset_x, offset_y)
                a4_page.merge_transformed_page(source_page, transform)
            else:
                writer.add_page(source_page)

            total_output_pages += 1
            page_map.append({
                "final_page": total_output_pages,
                "file_id": file_id,
                "file_name": file_name,
                "original_page": orig_page_num,
                "mode": mode
            })

    if total_output_pages != total_expected_pages:
        return {
            "success": False,
            "error": f"Integrity Failure: Expected {total_expected_pages} pages, but generated {total_output_pages} pages."
        }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "wb") as f_out:
        writer.write(f_out)

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return {"success": False, "error": "Output PDF file generation produced empty file."}

    verify_reader = PdfReader(output_path)
    if len(verify_reader.pages) != total_output_pages:
        return {
            "success": False,
            "error": f"Verification Failure: Output has {len(verify_reader.pages)} pages, expected {total_output_pages}."
        }

    return {
        "success": True,
        "total_files": len(files),
        "total_pages": total_output_pages,
        "output_path": output_path,
        "file_size": os.path.getsize(output_path),
        "page_map": page_map
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Action required: 'analyze' or 'merge'"}))
        sys.exit(1)

    action = sys.argv[1].lower()

    if action == "analyze":
        if len(sys.argv) < 3:
            print(json.dumps({"success": False, "error": "PDF file path required for analyze"}))
            sys.exit(1)
        file_path = sys.argv[2]
        password = sys.argv[3] if len(sys.argv) > 3 else None
        res = analyze_pdf(file_path, password)
        print(json.dumps(res, indent=2))

    elif action == "merge":
        if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
            with open(sys.argv[2], "r", encoding="utf-8") as f:
                job_config = json.load(f)
        else:
            raw_input = sys.stdin.read()
            if not raw_input.strip():
                print(json.dumps({"success": False, "error": "JSON config must be provided via stdin or file."}))
                sys.exit(1)
            job_config = json.loads(raw_input)

        res = merge_pdf_queue(job_config)
        print(json.dumps(res, indent=2))

    else:
        print(json.dumps({"success": False, "error": f"Unknown action: {action}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
