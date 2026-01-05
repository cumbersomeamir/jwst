#!/bin/bash
# Quick start script for JWST Results Dashboard

cd "$(dirname "$0")"

echo "=========================================="
echo "JWST Results Dashboard"
echo "=========================================="
echo ""
echo "Starting server on http://localhost:8000"
echo ""
echo "📊 Open in your browser:"
echo "   http://localhost:8000/web/index.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

python3 -m http.server 8000

