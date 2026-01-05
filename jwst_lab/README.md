# JWST Research Pipeline

A reproducible pipeline for analyzing JWST public data to identify candidate anomalies and novel sources.

## Overview

This pipeline:
1. Downloads JWST data from MAST using astroquery
2. Analyzes images to detect sources and compute morphology metrics
3. Identifies candidate anomalies using machine learning
4. Ranks candidates by composite score
5. Generates a comprehensive research report

**Important:** This pipeline identifies *candidate anomalies* that require verification. It does not claim discoveries without cross-validation.

## Quick Start

### 1. Set Up Environment

```bash
cd jwst_lab
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or: .venv\Scripts\activate  # On Windows

pip install -r requirements.txt
```

### 2. Configure Target

Edit `config.yaml` to set your target:

```yaml
target_mode: "object"  # or "coords"
target_name: "SMACS 0723"  # or your target name
radius_deg: 0.02  # Search radius
max_total_gb: 1.0  # Download size limit
```

For coordinate-based search:
```yaml
target_mode: "coords"
ra_deg: 110.8375
dec_deg: -73.4397
radius_deg: 0.02
```

### 3. Run Pipeline

```bash
python run_pipeline.py
```

This will:
- Check environment
- Download JWST data
- Analyze images
- Analyze spectra (if available)
- Rank candidates
- Generate report

## Output Structure

```
jwst_lab/
├── data/
│   ├── products/          # Downloaded FITS files
│   └── raw/               # (reserved for raw data)
├── outputs/
│   ├── figures/
│   │   ├── cutouts/       # Source cutout images
│   │   └── spectra/       # Spectrum plots
│   ├── tables/
│   │   ├── download_manifest.csv
│   │   ├── all_sources.csv
│   │   ├── anomaly_candidates_images.csv
│   │   ├── ranked_candidates.csv
│   │   └── ...
│   └── report/
│       └── REPORT.md      # Final research report
└── scripts/               # Pipeline scripts
```

## Configuration Options

Key parameters in `config.yaml`:

- **Target Selection:**
  - `target_mode`: "object" (by name) or "coords" (by coordinates)
  - `target_name`: Target name (e.g., "SMACS 0723")
  - `ra_deg`, `dec_deg`, `radius_deg`: Coordinates and search radius

- **Download Limits:**
  - `max_obs`: Maximum number of observations (default: 3)
  - `max_files`: Maximum number of files (default: 60)
  - `max_total_gb`: Maximum total download size in GB (default: 1.0)

- **Product Types:**
  - `product_types_image`: Image products to download (default: ["I2D"])
  - `product_types_spectra`: Spectra products (default: ["X1D"])

- **Analysis Parameters:**
  - `detection_threshold`: Source detection threshold in sigma (default: 3.0)
  - `min_snr`: Minimum SNR for candidates (default: 5.0)
  - `top_anomalies_per_image`: Number of top anomalies per image (default: 30)
  - `cutout_size`: Size of cutout images in pixels (default: 50)

## Individual Scripts

You can also run scripts individually:

```bash
python scripts/00_setup_check.py      # Check environment
python scripts/01_download_jwst.py    # Download data
python scripts/02_analyze_images.py   # Analyze images
python scripts/03_analyze_spectra.py  # Analyze spectra (optional)
python scripts/04_rank_candidates.py  # Rank candidates
python scripts/05_make_report.py      # Generate report
```

## Understanding the Results

### Anomaly Scores

Candidates are ranked by a composite score combining:
- **Anomaly Score (40%):** Isolation Forest anomaly detection on morphology features
- **SNR (30%):** Signal-to-noise ratio
- **Artifact Flags (20%):** Penalty for border sources, high ellipticity, NaN regions
- **Cross-frame Consistency (10%):** Bonus if source appears in multiple observations

### Verification Checklist

Before claiming any discovery, verify candidates by:
1. Checking other filters/epochs
2. Cross-matching with known catalogs (SIMBAD, Gaia)
3. Verifying not a PSF spike or cosmic ray
4. Replicating with different detection thresholds
5. Using independent analysis methods

See the generated `REPORT.md` for a complete verification checklist.

## Troubleshooting

### No observations found
- Check target name spelling
- Increase `radius_deg` in config
- Try coordinate-based search instead

### Download fails
- Check internet connection
- Reduce `max_total_gb` or `max_files`
- Some MAST servers may be temporarily unavailable

### Source detection issues
- Adjust `detection_threshold` in config
- Check that I2D products were downloaded (not raw data)
- Verify FITS files are not corrupted

### Memory issues
- Reduce `max_obs` or `max_files`
- Process images one at a time (modify scripts)

## Dependencies

See `requirements.txt` for full list. Key packages:
- `astroquery`: MAST data access
- `astropy`: FITS handling, WCS
- `photutils`, `sep`: Source detection
- `scikit-learn`: Anomaly detection
- `matplotlib`: Visualization

## Citation

If you use this pipeline in research, please cite:
- JWST data: [MAST](https://mast.stsci.edu)
- astroquery: [Ginsburg et al. 2019](https://doi.org/10.3847/1538-3881/aafc33)
- SEP: [Barbary 2016](https://doi.org/10.5281/zenodo.159035)

## License

This pipeline is provided as-is for research purposes. JWST data is public and available through MAST.

## Contact

For issues or questions about the pipeline, please check the code comments or modify as needed for your use case.


