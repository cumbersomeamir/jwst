# Quick Start Guide

## Setup (One-time)

```bash
cd jwst_lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run Pipeline

```bash
python run_pipeline.py
```

## Configuration

Edit `config.yaml` to change:
- Target name: `target_name: "SMACS 0723"`
- Search radius: `radius_deg: 0.02`
- Download limit: `max_total_gb: 1.0`

## Output

The final report will be generated at:
```
outputs/report/REPORT.md
```

All outputs are in the `outputs/` directory:
- `outputs/tables/ranked_candidates.csv` - Ranked anomaly candidates
- `outputs/figures/cutouts/` - Source cutout images
- `outputs/report/REPORT.md` - Complete research report


