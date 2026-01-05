#!/usr/bin/env python3
"""
Simple HTTP server to serve the JWST results dashboard.
Run this script and open http://localhost:8000 in your browser.
"""

import http.server
import socketserver
import os
from pathlib import Path

# Get the base directory (parent of web/)
BASE_DIR = Path(__file__).parent.parent
os.chdir(BASE_DIR)

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow loading CSV files
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

Handler = MyHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("=" * 60)
    print("JWST Results Dashboard Server")
    print("=" * 60)
    print(f"\n🌐 Server running at: http://localhost:{PORT}")
    print(f"📁 Serving from: {BASE_DIR}")
    print("\n📊 Open in your browser:")
    print(f"   http://localhost:{PORT}/web/index.html")
    print("\n⚠️  Press Ctrl+C to stop the server\n")
    print("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped.")

