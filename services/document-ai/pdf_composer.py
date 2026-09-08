"""
═══════════════════════════════════════════════════════════════
AK PRINT SEVA — Exact A4 PDF Composer & ZIP Builder
services/document-ai/pdf_composer.py
═══════════════════════════════════════════════════════════════
"""

import sys
import os
import json
import argparse
import zipfile
import re
from PIL import Image

def compose_a4_pdf(config_path, output_file):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    items = config.get('items', [])
    if not items:
        return {"success": False, "error": "No items provided for PDF creation"}

    req_type = config.get('type', 'combined')  # 'single', 'combined', 'zip'
    default_margin_mm = float(config.get('margin', 8.0))
    default_position = config.get('position', 'top') # 'top' or 'center'

    # A4 Dimensions at 300 DPI: 210 x 297 mm
    # 1 mm = 11.811 pixels at 300 DPI
    DPI = 300
    MM_TO_PX = DPI / 25.4
    A4_PORTRAIT_W = int(210 * MM_TO_PX)  # 2480
    A4_PORTRAIT_H = int(297 * MM_TO_PX)  # 3508

    pdf_pages = []
    individual_pdf_paths = []
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    for idx, item in enumerate(items):
        img_rel_url = item.get('image_url', '').lstrip('/')
        img_full_path = os.path.join(base_dir, img_rel_url)

        if not os.path.exists(img_full_path):
            continue

        try:
            doc_img = Image.open(img_full_path).convert('RGB')
        except Exception:
            continue

        doc_w, doc_h = doc_img.size

        # Determine Page Orientation (Auto / Portrait / Landscape)
        item_orientation = item.get('orientation', 'auto')
        if item_orientation == 'auto':
            page_orientation = 'landscape' if doc_w > (doc_h * 1.05) else 'portrait'
        else:
            page_orientation = item_orientation

        if page_orientation == 'landscape':
            canvas_w = A4_PORTRAIT_H  # 3508
            canvas_h = A4_PORTRAIT_W  # 2480
        else:
            canvas_w = A4_PORTRAIT_W  # 2480
            canvas_h = A4_PORTRAIT_H  # 3508

        # Margin in pixels
        margin_mm = float(item.get('margin', default_margin_mm))
        margin_px = int(margin_mm * MM_TO_PX)

        # Printable Box
        printable_w = max(100, canvas_w - (2 * margin_px))
        printable_h = max(100, canvas_h - (2 * margin_px))

        # Pure White A4 Canvas
        a4_canvas = Image.new('RGB', (canvas_w, canvas_h), (255, 255, 255))

        # Aspect-Ratio Preserving Fit (No Distortion)
        scale_w = printable_w / doc_w
        scale_h = printable_h / doc_h
        scale = min(scale_w, scale_h)

        new_w = int(doc_w * scale)
        new_h = int(doc_h * scale)

        resized_doc = doc_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Placement: Top-Aligned with Horizontal Centering
        pos_x = margin_px + (printable_w - new_w) // 2
        pos_mode = item.get('position', default_position)
        if pos_mode == 'center':
            pos_y = margin_px + (printable_h - new_h) // 2
        else: # top
            pos_y = margin_px

        a4_canvas.paste(resized_doc, (pos_x, pos_y))
        pdf_pages.append(a4_canvas)

        # Individual PDF generation if requested
        if req_type == 'zip' or req_type == 'individual':
            raw_title = item.get('title') or os.path.splitext(os.path.basename(img_full_path))[0]
            clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', raw_title)[:30]
            single_name = f"doc_{idx+1:02d}_{clean_title}-a4.pdf"
            single_path = os.path.join(os.path.dirname(output_file), single_name)
            a4_canvas.save(single_path, "PDF", resolution=300.0, quality=95)
            individual_pdf_paths.append(single_path)

    if not pdf_pages:
        return {"success": False, "error": "No valid document images could be processed into PDF."}

    if req_type == 'zip':
        # Create ZIP archive containing all individual PDFs
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for p in individual_pdf_paths:
                zf.write(p, arcname=os.path.basename(p))
                try:
                    os.remove(p)
                except Exception:
                    pass
    else:
        # Save Combined A4 PDF (Each document = 1 Page)
        first_page = pdf_pages[0]
        other_pages = pdf_pages[1:] if len(pdf_pages) > 1 else []
        first_page.save(
            output_file,
            "PDF",
            resolution=300.0,
            save_all=True,
            append_images=other_pages,
            quality=95
        )

    file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0

    return {
        "success": True,
        "output_file": output_file,
        "pages_count": len(pdf_pages),
        "file_size": file_size
    }

def main():
    parser = argparse.ArgumentParser(description="A4 PDF Composer")
    parser.add_argument("--config", required=True, help="Path to config JSON")
    parser.add_argument("--output", required=True, help="Output PDF/ZIP path")
    args = parser.parse_args()

    result = compose_a4_pdf(args.config, args.output)
    print(json.dumps(result))

if __name__ == "__main__":
    main()
