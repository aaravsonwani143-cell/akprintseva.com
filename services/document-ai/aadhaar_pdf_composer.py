"""
═══════════════════════════════════════════════════════════════
AK PRINT SEVA — AADHAAR CARD PRINT MAKER
services/document-ai/aadhaar_pdf_composer.py
A4 Layout & Copies Engine (Vertical, Horizontal, Separate & ZIP)
═══════════════════════════════════════════════════════════════
"""

import sys
import os
import json
import argparse
import zipfile
import re
from PIL import Image

def compose_aadhaar_page(front_img, back_img, layout_type='vertical', margin_mm=8.0, position='top'):
    """
    Renders 1 complete A4 canvas sheet (300 DPI: 2480 x 3508 px) with Front and Back.
    """
    DPI = 300
    MM_TO_PX = DPI / 25.4
    A4_W = int(210 * MM_TO_PX)  # 2480
    A4_H = int(297 * MM_TO_PX)  # 3508
    margin_px = int(margin_mm * MM_TO_PX)

    printable_w = A4_W - (2 * margin_px)
    printable_h = A4_H - (2 * margin_px)

    canvas = Image.new('RGB', (A4_W, A4_H), (255, 255, 255))

    # Standard Aadhaar Card Aspect Ratio: 86mm x 54mm (CR-80 ID-1 standard)
    # Exact 86mm width = 1015 px @ 300 DPI -> 1:1 Pixel Match with zero interpolation blur
    card_target_w = int(86.0 * MM_TO_PX) # ~1015 px wide

    if layout_type == 'vertical':
        # Front on top, Back on bottom
        cards = []
        if front_img:
            cards.append(front_img)
        if back_img:
            cards.append(back_img)

        if not cards:
            return canvas

        gap_px = int(8 * MM_TO_PX) # 8mm gap between Front and Back
        curr_y = margin_px + int(4 * MM_TO_PX)

        for card in cards:
            cw, ch = card.size
            scale = card_target_w / float(cw)
            nw = int(cw * scale)
            nh = int(ch * scale)
            resized = card.resize((nw, nh), Image.Resampling.LANCZOS)
            pos_x = margin_px + (printable_w - nw) // 2
            canvas.paste(resized, (pos_x, curr_y))
            curr_y += nh + gap_px

    elif layout_type == 'horizontal':
        # Front and Back Side by Side (scaled down to fit width)
        half_w = (printable_w - int(10 * MM_TO_PX)) // 2
        cards = [front_img, back_img]
        curr_x = margin_px
        curr_y = margin_px

        for card in cards:
            if not card:
                continue
            cw, ch = card.size
            scale = half_w / float(cw)
            nw = int(cw * scale)
            nh = int(ch * scale)
            resized = card.resize((nw, nh), Image.Resampling.LANCZOS)
            canvas.paste(resized, (curr_x, curr_y))
            curr_x += nw + int(10 * MM_TO_PX)

    elif layout_type == 'front_only':
        if front_img:
            cw, ch = front_img.size
            scale = card_target_w / float(cw)
            nw = int(cw * scale)
            nh = int(ch * scale)
            resized = front_img.resize((nw, nh), Image.Resampling.LANCZOS)
            pos_x = margin_px + (printable_w - nw) // 2
            canvas.paste(resized, (pos_x, margin_px))

    elif layout_type == 'back_only':
        if back_img:
            cw, ch = back_img.size
            scale = card_target_w / float(cw)
            nw = int(cw * scale)
            nh = int(ch * scale)
            resized = back_img.resize((nw, nh), Image.Resampling.LANCZOS)
            pos_x = margin_px + (printable_w - nw) // 2
            canvas.paste(resized, (pos_x, margin_px))

    return canvas

def generate_aadhaar_pdf(config_path, output_file):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    sets = config.get('sets', [])
    if not sets:
        return {"success": False, "error": "No Aadhaar sets provided."}

    layout_type = config.get('layout', 'vertical')
    copies = int(config.get('copies', 1))
    margin_mm = float(config.get('margin', 8.0))
    req_type = config.get('type', 'combined') # 'combined', 'single', 'zip'

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    pdf_pages = []
    individual_pdf_paths = []

    for set_idx, a_set in enumerate(sets):
        front_url = a_set.get('front_url', '').lstrip('/')
        back_url = a_set.get('back_url', '').lstrip('/')

        front_path = os.path.join(base_dir, front_url) if front_url else None
        back_path = os.path.join(base_dir, back_url) if back_url else None

        front_img = None
        back_img = None

        if front_path and os.path.exists(front_path):
            try:
                front_img = Image.open(front_path).convert('RGB')
            except Exception:
                pass

        if back_path and os.path.exists(back_path):
            try:
                back_img = Image.open(back_path).convert('RGB')
            except Exception:
                pass

        if not front_img and not back_img:
            continue

        if layout_type == 'separate':
            # Page 1: Front, Page 2: Back
            p1 = compose_aadhaar_page(front_img, None, layout_type='front_only', margin_mm=margin_mm)
            p2 = compose_aadhaar_page(None, back_img, layout_type='back_only', margin_mm=margin_mm)
            for _ in range(copies):
                pdf_pages.extend([p1, p2])
        else:
            page_canvas = compose_aadhaar_page(front_img, back_img, layout_type=layout_type, margin_mm=margin_mm)
            for _ in range(copies):
                pdf_pages.append(page_canvas)

        if req_type == 'zip':
            single_name = f"aadhaar_set_{set_idx+1:02d}.pdf"
            single_path = os.path.join(os.path.dirname(output_file), single_name)
            if layout_type == 'separate':
                p1 = compose_aadhaar_page(front_img, None, layout_type='front_only', margin_mm=margin_mm)
                p2 = compose_aadhaar_page(None, back_img, layout_type='back_only', margin_mm=margin_mm)
                p1.save(single_path, "PDF", resolution=300.0, save_all=True, append_images=[p2], quality=100, subsampling=0)
            else:
                p = compose_aadhaar_page(front_img, back_img, layout_type=layout_type, margin_mm=margin_mm)
                p.save(single_path, "PDF", resolution=300.0, quality=100, subsampling=0)
            individual_pdf_paths.append(single_path)

    if not pdf_pages:
        return {"success": False, "error": "Could not compose PDF pages from provided images."}

    if req_type == 'zip':
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for p in individual_pdf_paths:
                zf.write(p, arcname=os.path.basename(p))
                try:
                    os.remove(p)
                except Exception:
                    pass
    else:
        first_page = pdf_pages[0]
        other_pages = pdf_pages[1:] if len(pdf_pages) > 1 else []
        first_page.save(
            output_file,
            "PDF",
            resolution=300.0,
            save_all=True,
            append_images=other_pages,
            quality=100,
            subsampling=0
        )

    file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0

    return {
        "success": True,
        "output_file": output_file,
        "pages_count": len(pdf_pages),
        "file_size": file_size
    }

def main():
    parser = argparse.ArgumentParser(description="Aadhaar PDF Composer")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = generate_aadhaar_pdf(args.config, args.output)
    print(json.dumps(result))

if __name__ == "__main__":
    main()
