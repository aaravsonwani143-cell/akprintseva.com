#!/usr/bin/env python3
"""
Unit Test Suite for Cyber Cafe Smart PDF Print Queue Engine
services/pdf/test_queue_engine.py
"""

import os
import sys
import tempfile
import unittest
from pypdf import PdfWriter
from pdf_queue_processor import analyze_pdf, merge_pdf_queue


def create_dummy_pdf(path: str, pages: int, is_landscape: bool = False, text_prefix: str = "Page"):
    writer = PdfWriter()
    w, h = (842, 595) if is_landscape else (595, 842)
    for i in range(pages):
        writer.add_blank_page(width=w, height=h)
    with open(path, "wb") as f:
        writer.write(f)


class TestPdfQueueProcessor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pdf_a = os.path.join(self.temp_dir.name, "doc_a.pdf")
        self.pdf_b = os.path.join(self.temp_dir.name, "doc_b.pdf")
        self.pdf_c = os.path.join(self.temp_dir.name, "doc_c.pdf")

        create_dummy_pdf(self.pdf_a, pages=2, is_landscape=False)
        create_dummy_pdf(self.pdf_b, pages=5, is_landscape=True)
        create_dummy_pdf(self.pdf_c, pages=3, is_landscape=False)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_analyze(self):
        res = analyze_pdf(self.pdf_b)
        self.assertTrue(res["success"])
        self.assertEqual(res["page_count"], 5)
        self.assertEqual(res["pages"][0]["orientation"], "Landscape")

    def test_merge_sequential_preserve_original(self):
        out_path = os.path.join(self.temp_dir.name, "merged_orig.pdf")
        config = {
            "files": [
                {"path": self.pdf_a, "original_name": "Doc A"},
                {"path": self.pdf_b, "original_name": "Doc B"},
                {"path": self.pdf_c, "original_name": "Doc C"}
            ],
            "output_path": out_path,
            "page_size_mode": "preserve_original"
        }
        res = merge_pdf_queue(config)
        self.assertTrue(res["success"])
        self.assertEqual(res["total_pages"], 10)  # 2 + 5 + 3 = 10
        self.assertEqual(len(res["page_map"]), 10)

    def test_merge_reorder(self):
        out_path = os.path.join(self.temp_dir.name, "merged_reorder.pdf")
        config = {
            "files": [
                {"path": self.pdf_c, "original_name": "Doc C"},
                {"path": self.pdf_a, "original_name": "Doc A"}
            ],
            "output_path": out_path,
            "page_size_mode": "preserve_original"
        }
        res = merge_pdf_queue(config)
        self.assertTrue(res["success"])
        self.assertEqual(res["total_pages"], 5)  # 3 + 2 = 5
        self.assertEqual(res["page_map"][0]["file_name"], "Doc C")
        self.assertEqual(res["page_map"][3]["file_name"], "Doc A")

    def test_normalize_a4(self):
        out_path = os.path.join(self.temp_dir.name, "merged_a4.pdf")
        config = {
            "files": [
                {"path": self.pdf_a, "original_name": "Doc A"},
                {"path": self.pdf_b, "original_name": "Doc B"}
            ],
            "output_path": out_path,
            "page_size_mode": "normalize_a4",
            "margin_mm": 5.0
        }
        res = merge_pdf_queue(config)
        self.assertTrue(res["success"])
        self.assertEqual(res["total_pages"], 7)  # 2 + 5 = 7


if __name__ == "__main__":
    unittest.main()
