# JWST Results Dashboard

Interactive web dashboard for viewing JWST anomaly detection study results.

## Quick Start

### Option 1: Simple HTTP Server (Recommended)

```bash
cd jwst_lab
python3 -m http.server 8000
```

Then open in your browser:
```
http://localhost:8000/web/index.html
```

### Option 2: Using the Provided Server Script

```bash
cd jwst_lab
python web/server.py
```

Then open:
```
http://localhost:8000/web/index.html
```

### Option 3: Open Directly

You can also open `web/index.html` directly in your browser, but CSV data loading may be blocked by browser security. Use a local server for full functionality.

## Features

- **Interactive Visualizations**: Charts showing SNR distribution, anomaly scores, verification results
- **Top Candidates Table**: Detailed view of highest-ranked anomaly candidates
- **Verification Results**: Complete verification analysis for each candidate
- **Comprehensive Statistics**: Key metrics and findings
- **Next Steps**: Actionable recommendations for follow-up

## Requirements

- Modern web browser (Chrome, Firefox, Safari, Edge)
- Local HTTP server (for CSV data loading)
- No additional dependencies (uses CDN for Chart.js)

## Troubleshooting

If charts don't load:
1. Check browser console for errors (F12)
2. Ensure CSV files exist in `outputs/tables/`
3. Verify server is running and accessible
4. Check CORS headers if using a different server

