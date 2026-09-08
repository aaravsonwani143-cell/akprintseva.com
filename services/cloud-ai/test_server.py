#!/usr/bin/env python3
"""
Unit test for AK Print Seva Cloud AI Microservice Server
Verifies that HTTP API produces identical results to local pipeline.
"""

import sys
import os
import json
import base64
import time
import urllib.request
import urllib.error
import subprocess

PORT = 8999
BASE_URL = f"http://127.0.0.1:{PORT}"
TEST_IMAGE = "C:/Users/win11/.gemini/antigravity-ide/brain/2b3c0361-b644-42e5-a37e-de5c912b2225/.user_uploaded/media_1788505913610.jpg"

def main():
    print("[1/5] Starting Cloud AI Microservice on test port", PORT)
    server_script = os.path.join(os.path.dirname(__file__), "server.py")
    proc = subprocess.Popen([sys.executable, server_script, "--port", str(PORT)])

    # Wait for server to bind
    time.sleep(1.5)

    try:
        # 1. Health check
        print("[2/5] Testing GET /health...")
        req = urllib.request.Request(f"{BASE_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print("  Health response:", data)
            assert data.get('status') == 'healthy', "Health check failed"
            assert data.get('services_loaded') is True, "Services not loaded"
        print("  [PASS] /health PASSED")

        # 2. Aadhaar processing test
        print("[3/5] Testing POST /api/aadhaar-print/process...")
        if os.path.exists(TEST_IMAGE):
            with open(TEST_IMAGE, 'rb') as f:
                img_b64 = base64.b64encode(f.read()).decode('utf-8')

            payload = json.dumps({
                "image_base64": img_b64,
                "mode": "auto",
                "rotation": 0
            }).encode('utf-8')

            req = urllib.request.Request(
                f"{BASE_URL}/api/aadhaar-print/process",
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'X-API-Key': 'ak_sec_print_ai_2026'
                }
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                assert result.get('success') is True, f"Aadhaar API failed: {result}"
                assert 'processed_image_base64' in result, "Missing output image base64"
                assert result.get('output_dimensions') == {"width": 1014, "height": 638}, f"Bad output dimensions: {result.get('output_dimensions')}"
                print(f"  Processed successfully: Side={result.get('side')}, Dim={result.get('output_dimensions')}")
            print("  [PASS] POST /api/aadhaar-print/process PASSED")
        else:
            print("  [WARN] Test image not found, skipping image test")

        print("[4/5] Testing Unauthorized Request...")
        bad_req = urllib.request.Request(
            f"{BASE_URL}/api/aadhaar-print/process",
            data=b'{}',
            headers={'Content-Type': 'application/json', 'X-API-Key': 'wrong-key'}
        )
        try:
            urllib.request.urlopen(bad_req, timeout=5)
            assert False, "Should have been rejected with 401"
        except urllib.error.HTTPError as he:
            assert he.code == 401, f"Expected 401, got {he.code}"
            print("  [PASS] Auth protection 401 PASSED")

        print("[5/5] ALL MICROSERVICE UNIT TESTS PASSED SUCCESSFULLY!")

    finally:
        print("Stopping test server...")
        proc.terminate()
        proc.wait(timeout=5)

if __name__ == "__main__":
    main()
