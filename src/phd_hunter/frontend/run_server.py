#!/usr/bin/env python3
"""Simple HTTP server that serves frontend + papers directory."""

import http.server
import socketserver
import os
from pathlib import Path

FRONTEND_DIR = Path(__file__).parent
PAPERS_DIR = Path(__file__).parent.parent.parent / "papers"

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler that maps /papers/ to the papers directory."""

    def translate_path(self, path):
        # Check if path starts with /papers/
        if path.startswith('/papers/'):
            # Map to PAPERS_DIR
            relative_path = path[8:]  # Remove '/papers/'
            return str(PAPERS_DIR / relative_path)
        else:
            # Default: serve from FRONTEND_DIR
            return super().translate_path(path)

    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

PORT = 8080

print(f"Starting PhD Hunter Frontend Server...")
print(f"Serving frontend: {FRONTEND_DIR}")
print(f"  - http://localhost:{PORT}/")
print(f"  - http://localhost:{PORT}/papers/  →  {PAPERS_DIR}")
print(f"\nPress Ctrl+C to stop.\n")

with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
