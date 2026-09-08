#!/usr/bin/env python3
"""
═════════════════════════════════════════════════════════════════════════
AK PRINT SEVA — High-Performance Cloud AI Microservice Server
services/cloud-ai/server.py

Zero-dependency HTTP server for deploying Document AI on free cloud
containers (Render / Hugging Face Spaces / Railway / Koyeb).
═════════════════════════════════════════════════════════════════════════
"""

import sys
import os
import json
import base64
import argparse
import tempfile
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Look for services directory across possible deployment roots
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
possible_roots = [
    CURRENT_DIR,
    os.path.abspath(os.path.join(CURRENT_DIR, '..')),
    os.path.abspath(os.path.join(CURRENT_DIR, '..', '..')),
    os.getcwd()
]

for r in possible_roots:
    d = os.path.join(r, 'services', 'document-ai')
    p = os.path.join(r, 'services', 'pdf')
    if os.path.isdir(d):
        if d not in sys.path:
            sys.path.insert(0, d)
        if p not in sys.path:
            sys.path.insert(0, p)
        break

# Import protected engines safely
IMPORT_ERROR = None
try:
    import aadhaar_processor
    import doc_processor
    import aadhaar_pdf_composer
    import pdf_composer
    import pdf_queue_processor
    SERVICES_LOADED = True
except Exception as e:
    IMPORT_ERROR = f"{type(e).__name__}: {str(e)}"
    print(f"[WARN] Some services failed to import on startup: {IMPORT_ERROR}")
    SERVICES_LOADED = False

API_KEY = os.environ.get("API_KEY", "ak_sec_print_ai_2026")


class ThreadingServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class CloudAIRequestHandler(BaseHTTPRequestHandler):
    server_version = "AKPrintSeva-CloudAI/1.0"

    def _send_json(self, data, status_code=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-API-Key')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-API-Key')
        self.end_headers()

    def _verify_auth(self):
        if not API_KEY:
            return True
        key_header = self.headers.get('X-API-Key') or ''
        auth_header = self.headers.get('Authorization') or ''
        if auth_header.startswith('Bearer '):
            auth_token = auth_header.split(' ', 1)[1].strip()
        else:
            auth_token = ''
        return (key_header == API_KEY) or (auth_token == API_KEY)

    def _read_json_body(self):
        content_len = int(self.headers.get('Content-Length', 0))
        if content_len == 0:
            return None
        raw_data = self.rfile.read(content_len)
        return json.loads(raw_data.decode('utf-8'))

    def do_GET(self):
        path = self.path.split('?')[0].rstrip('/')
        if path == '' or path == '/health':
            self._send_json({
                "status": "healthy",
                "service": "AK Print Seva Cloud AI",
                "version": "1.0.0",
                "python_version": sys.version,
                "services_loaded": SERVICES_LOADED,
                "import_error": IMPORT_ERROR
            })
            return

        self._send_json({"error": "Endpoint not found"}, status_code=404)

    def do_POST(self):
        if not self._verify_auth():
            self._send_json({"success": False, "error": "Unauthorized. Invalid X-API-Key."}, status_code=401)
            return

        path = self.path.split('?')[0].rstrip('/')

        try:
            payload = self._read_json_body()
            if not payload:
                self._send_json({"success": False, "error": "Empty or invalid JSON body"}, status_code=400)
                return

            if path == '/api/aadhaar-print/process':
                self._handle_aadhaar_process(payload)
            elif path == '/api/aadhaar-print/generate-pdf':
                self._handle_aadhaar_pdf(payload)
            elif path == '/api/smart-document/process':
                self._handle_smart_document_process(payload)
            elif path == '/api/multi-pdf-print/combine':
                self._handle_pdf_queue_combine(payload)
            else:
                self._send_json({"success": False, "error": f"Unknown endpoint: {path}"}, status_code=404)

        except Exception as e:
            traceback.print_exc()
            self._send_json({
                "success": False,
                "error": f"Internal Server Error: {str(e)}",
                "trace": traceback.format_exc()
            }, status_code=500)

    def _handle_aadhaar_process(self, payload):
        """Processes an Aadhaar Card image via aadhaar_processor.py"""
        img_b64 = payload.get('image_base64')
        if not img_b64:
            self._send_json({"success": False, "error": "Missing 'image_base64' in payload."}, status_code=400)
            return

        mode = payload.get('mode', 'auto')
        rotation = int(payload.get('rotation', 0))
        corners = payload.get('corners')
        side_override = payload.get('side')

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as in_f:
            in_path = in_f.name
            in_f.write(base64.b64decode(img_b64))

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as out_f:
            out_path = out_f.name

        try:
            result = aadhaar_processor.process_aadhaar_pipeline(
                input_path=in_path,
                output_path=out_path,
                mode=mode,
                corners=corners,
                rotation=rotation,
                side_override=side_override
            )

            if result.get('success') and os.path.exists(out_path):
                with open(out_path, 'rb') as f:
                    processed_b64 = base64.b64encode(f.read()).decode('utf-8')
                result['processed_image_base64'] = processed_b64

            self._send_json(result)
        finally:
            if os.path.exists(in_path):
                os.remove(in_path)
            if os.path.exists(out_path):
                os.remove(out_path)

    def _handle_aadhaar_pdf(self, payload):
        """Generates print-ready A4 PDF or ZIP via aadhaar_pdf_composer.py"""
        # payload is the exact config dict expected by aadhaar_pdf_composer
        # If image paths in payload are base64, write them to temp files first
        temp_files_to_clean = []
        try:
            if 'sets' in payload and isinstance(payload['sets'], list):
                for s in payload['sets']:
                    for side_key in ['front', 'back']:
                        if side_key in s and s[side_key] and s[side_key].startswith('data:'):
                            # data URI base64
                            b64_str = s[side_key].split(',', 1)[1]
                            tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                            tmp.write(base64.b64decode(b64_str))
                            tmp.close()
                            s[side_key] = tmp.name
                            temp_files_to_clean.append(tmp.name)
                        elif side_key in s and s[side_key] and len(s[side_key]) > 500 and not os.path.exists(s[side_key]):
                            # direct base64
                            tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                            tmp.write(base64.b64decode(s[side_key]))
                            tmp.close()
                            s[side_key] = tmp.name
                            temp_files_to_clean.append(tmp.name)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as cfg_f:
                cfg_path = cfg_f.name
                json.dump(payload, cfg_f)
            temp_files_to_clean.append(cfg_path)

            req_type = payload.get('type', 'combined')
            ext = '.zip' if req_type == 'zip' else '.pdf'
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as out_f:
                out_path = out_f.name
            temp_files_to_clean.append(out_path)

            result = aadhaar_pdf_composer.generate_aadhaar_pdf(cfg_path, out_path)

            if result.get('success') and os.path.exists(out_path):
                with open(out_path, 'rb') as f:
                    result['file_base64'] = base64.b64encode(f.read()).decode('utf-8')

            self._send_json(result)
        finally:
            for tf in temp_files_to_clean:
                if os.path.exists(tf):
                    try:
                        os.remove(tf)
                    except Exception:
                        pass

    def _handle_smart_document_process(self, payload):
        """Processes generic document scan via doc_processor.py"""
        img_b64 = payload.get('image_base64')
        if not img_b64:
            self._send_json({"success": False, "error": "Missing 'image_base64'"}, status_code=400)
            return

        mode = payload.get('mode', 'auto')
        rotation = int(payload.get('rotation', 0))
        corners = payload.get('corners')

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as in_f:
            in_path = in_f.name
            in_f.write(base64.b64decode(img_b64))

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as out_f:
            out_path = out_f.name

        try:
            result = doc_processor.process_document(
                image_path=in_path,
                output_path=out_path,
                mode=mode,
                corners=corners,
                rotation=rotation
            )

            if result.get('success') and os.path.exists(out_path):
                with open(out_path, 'rb') as f:
                    result['processed_image_base64'] = base64.b64encode(f.read()).decode('utf-8')

            self._send_json(result)
        finally:
            if os.path.exists(in_path):
                os.remove(in_path)
            if os.path.exists(out_path):
                os.remove(out_path)

    def _handle_pdf_queue_combine(self, payload):
        """Merges multiple PDFs into one continuous print stream via pdf_queue_processor.py"""
        files_data = payload.get('files', [])
        mode = payload.get('page_size_mode', 'preserve_original')
        margin_mm = float(payload.get('margin_mm', 5.0))

        temp_files_to_clean = []
        resolved_files = []

        try:
            for item in files_data:
                b64 = item.get('content_base64')
                if not b64:
                    continue
                tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                tmp.write(base64.b64decode(b64))
                tmp.close()
                temp_files_to_clean.append(tmp.name)

                resolved_files.append({
                    'file_id': item.get('file_id', os.path.basename(tmp.name)),
                    'path': tmp.name,
                    'original_name': item.get('original_name', 'document.pdf'),
                    'password': item.get('password'),
                    'excluded_pages': item.get('excluded_pages', [])
                })

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as out_f:
                out_path = out_f.name
            temp_files_to_clean.append(out_path)

            task_cfg = {
                'files': resolved_files,
                'output_path': out_path,
                'page_size_mode': mode,
                'margin_mm': margin_mm
            }

            result = pdf_queue_processor.merge_pdfs(task_cfg)

            if result.get('success') and os.path.exists(out_path):
                with open(out_path, 'rb') as f:
                    result['combined_pdf_base64'] = base64.b64encode(f.read()).decode('utf-8')

            self._send_json(result)
        finally:
            for tf in temp_files_to_clean:
                if os.path.exists(tf):
                    try:
                        os.remove(tf)
                    except Exception:
                        pass


def main():
    parser = argparse.ArgumentParser(description="AK Print Seva Cloud AI Microservice")
    parser.add_argument("--host", default="0.0.0.0", help="Binding host")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    args = parser.parse_args()

    server_address = (args.host, args.port)
    httpd = ThreadingServer(server_address, CloudAIRequestHandler)
    print(f"[START] AK Print Seva Cloud AI Microservice running at http://{args.host}:{args.port}")
    print(f"[AUTH] API Auth: {'Enabled' if API_KEY else 'Disabled (Public)'}")
    print("Press Ctrl+C to terminate.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()


if __name__ == "__main__":
    main()
