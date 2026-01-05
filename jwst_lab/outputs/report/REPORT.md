# JWST Anomaly Candidate Research Report

**Generated:** 2026-01-05 12:56:44

---

## Executive Summary

This report presents candidate anomalies identified in JWST public data.
**Important:** These are candidate anomalies requiring verification.
They should not be interpreted as 'never discovered before' without
further cross-validation with other datasets and analysis methods.

## Data Summary

**Target:** M82
**Mode:** coords

### Observations Downloaded

| Observation ID | Instrument | Files | Size (GB) |
|----------------|------------|-------|-----------|
| test_obs_1 | NIRCAM | 1 | 0.00 |
| test_obs_2 | NIRCAM | 1 | 0.00 |
| test_obs_3 | NIRCAM | 1 | 0.00 |

### Product Types

| Product Type | Count | Total Size (GB) |
|-------------|-------|-----------------|
| I2D | 3 | 0.01 |

## Pipeline Steps

1. **Data Download:** Queried MAST for JWST observations matching target criteria
2. **Source Detection:** Used SEP/photutils for source extraction from I2D images
3. **Morphology Analysis:** Computed metrics: SNR, concentration, asymmetry, eccentricity, edge density
4. **Anomaly Detection:** Applied Isolation Forest on morphology features
5. **Ranking:** Composite score based on anomaly score, SNR, artifact flags, cross-frame consistency

## Top 20 Anomaly Candidates

Candidates are ranked by composite score combining anomaly score, SNR,
artifact flags, and cross-frame consistency.

### Candidate #1

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F115W
- **Observation ID:** test_obs_1
- **Coordinates:** RA=149.023724°, Dec=69.672366°
- **Pixel Position:** x=319.0, y=437.8
- **SNR:** 422.8
- **Composite Score:** 0.922
- **Anomaly Score:** 0.705
- **Key Features:** SNR=422.8, ecc=0.00, asym=0.87
- **Cutout:** ![Candidate #1](outputs/figures/cutouts/test_jwst_image_1_i2d_anomaly_388.png)

### Candidate #2

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F115W
- **Observation ID:** test_obs_1
- **Coordinates:** RA=149.024119°, Dec=69.678858°
- **Pixel Position:** x=317.7, y=502.7
- **SNR:** 422.8
- **Composite Score:** 0.800
- **Anomaly Score:** 0.737
- **Key Features:** SNR=422.8, ecc=0.94, asym=0.88
- **Flags:** high_ellipticity
- **Cutout:** ![Candidate #2](outputs/figures/cutouts/test_jwst_image_1_i2d_anomaly_442.png)

### Candidate #3

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F115W
- **Observation ID:** test_obs_1
- **Coordinates:** RA=149.017043°, Dec=69.675234°
- **Pixel Position:** x=342.2, y=466.5
- **SNR:** 422.8
- **Composite Score:** 0.774
- **Anomaly Score:** 0.644
- **Key Features:** SNR=422.8, ecc=0.00, asym=0.59
- **Cutout:** ![Candidate #3](outputs/figures/cutouts/test_jwst_image_1_i2d_anomaly_413.png)

### Candidate #4

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F200W
- **Observation ID:** test_obs_2
- **Coordinates:** RA=148.991924°, Dec=69.688045°
- **Pixel Position:** x=429.5, y=594.5
- **SNR:** 350.7
- **Composite Score:** 0.756
- **Anomaly Score:** 0.658
- **Key Features:** SNR=350.7, ecc=0.00, asym=0.42
- **Cutout:** ![Candidate #4](outputs/figures/cutouts/test_jwst_image_2_i2d_anomaly_499.png)

### Candidate #5

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F115W
- **Observation ID:** test_obs_1
- **Coordinates:** RA=149.015692°, Dec=69.678935°
- **Pixel Position:** x=347.0, y=503.5
- **SNR:** 422.8
- **Composite Score:** 0.755
- **Anomaly Score:** 0.718
- **Key Features:** SNR=422.8, ecc=0.95, asym=0.83
- **Flags:** high_ellipticity
- **Cutout:** ![Candidate #5](outputs/figures/cutouts/test_jwst_image_1_i2d_anomaly_445.png)

### Candidate #6

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F444W
- **Observation ID:** test_obs_3
- **Coordinates:** RA=148.930644°, Dec=69.655373°
- **Pixel Position:** x=642.5, y=267.8
- **SNR:** 231.9
- **Composite Score:** 0.720
- **Anomaly Score:** 0.678
- **Key Features:** SNR=231.9, ecc=0.00, asym=0.83
- **Cutout:** ![Candidate #6](outputs/figures/cutouts/test_jwst_image_3_i2d_anomaly_216.png)

### Candidate #7

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F115W
- **Observation ID:** test_obs_1
- **Coordinates:** RA=148.962197°, Dec=69.657786°
- **Pixel Position:** x=532.8, y=291.9
- **SNR:** 97.1
- **Composite Score:** 0.704
- **Anomaly Score:** 0.711
- **Key Features:** SNR=97.1, ecc=0.00, asym=0.87
- **Cutout:** ![Candidate #7](outputs/figures/cutouts/test_jwst_image_1_i2d_anomaly_261.png)

### Candidate #8

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F115W
- **Observation ID:** test_obs_1
- **Coordinates:** RA=149.012388°, Dec=69.673925°
- **Pixel Position:** x=358.4, y=453.4
- **SNR:** 422.8
- **Composite Score:** 0.687
- **Anomaly Score:** 0.609
- **Key Features:** SNR=422.8, ecc=0.00, asym=0.86
- **Cutout:** ![Candidate #8](outputs/figures/cutouts/test_jwst_image_1_i2d_anomaly_402.png)

### Candidate #9

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F200W
- **Observation ID:** test_obs_2
- **Coordinates:** RA=148.992398°, Dec=69.692134°
- **Pixel Position:** x=427.9, y=635.4
- **SNR:** 350.7
- **Composite Score:** 0.677
- **Anomaly Score:** 0.626
- **Key Features:** SNR=350.7, ecc=0.00, asym=0.83
- **Cutout:** ![Candidate #9](outputs/figures/cutouts/test_jwst_image_2_i2d_anomaly_536.png)

### Candidate #10

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F444W
- **Observation ID:** test_obs_3
- **Coordinates:** RA=149.047363°, Dec=69.657616°
- **Pixel Position:** x=236.7, y=290.4
- **SNR:** 348.7
- **Composite Score:** 0.674
- **Anomaly Score:** 0.625
- **Key Features:** SNR=348.7, ecc=0.00, asym=0.83
- **Cutout:** ![Candidate #10](outputs/figures/cutouts/test_jwst_image_3_i2d_anomaly_238.png)

### Candidate #11

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F200W
- **Observation ID:** test_obs_2
- **Coordinates:** RA=148.982789°, Dec=69.686103°
- **Pixel Position:** x=461.2, y=575.1
- **SNR:** 350.7
- **Composite Score:** 0.662
- **Anomaly Score:** 0.620
- **Key Features:** SNR=350.7, ecc=0.00, asym=0.83
- **Cutout:** ![Candidate #11](outputs/figures/cutouts/test_jwst_image_2_i2d_anomaly_484.png)

### Candidate #12

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F444W
- **Observation ID:** test_obs_3
- **Coordinates:** RA=148.948641°, Dec=69.656501°
- **Pixel Position:** x=579.9, y=279.1
- **SNR:** 231.9
- **Composite Score:** 0.646
- **Anomaly Score:** 0.648
- **Key Features:** SNR=231.9, ecc=0.58, asym=0.90
- **Cutout:** ![Candidate #12](outputs/figures/cutouts/test_jwst_image_3_i2d_anomaly_225.png)

### Candidate #13

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F115W
- **Observation ID:** test_obs_1
- **Coordinates:** RA=149.025705°, Dec=69.680271°
- **Pixel Position:** x=312.2, y=516.9
- **SNR:** 422.0
- **Composite Score:** 0.634
- **Anomaly Score:** 0.669
- **Key Features:** SNR=422.0, ecc=0.89, asym=0.85
- **Flags:** high_ellipticity
- **Cutout:** ![Candidate #13](outputs/figures/cutouts/test_jwst_image_1_i2d_anomaly_461.png)

### Candidate #14

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F115W
- **Observation ID:** test_obs_1
- **Coordinates:** RA=149.045644°, Dec=69.679110°
- **Pixel Position:** x=242.9, y=505.3
- **SNR:** 304.9
- **Composite Score:** 0.619
- **Anomaly Score:** 0.615
- **Key Features:** SNR=304.9, ecc=0.45, asym=0.81
- **Cutout:** ![Candidate #14](outputs/figures/cutouts/test_jwst_image_1_i2d_anomaly_447.png)

### Candidate #15

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F200W
- **Observation ID:** test_obs_2
- **Coordinates:** RA=149.063831°, Dec=69.685638°
- **Pixel Position:** x=179.9, y=570.7
- **SNR:** 350.0
- **Composite Score:** 0.606
- **Anomaly Score:** 0.597
- **Key Features:** SNR=350.0, ecc=0.20, asym=0.78
- **Cutout:** ![Candidate #15](outputs/figures/cutouts/test_jwst_image_2_i2d_anomaly_481.png)

### Candidate #16

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F115W
- **Observation ID:** test_obs_1
- **Coordinates:** RA=149.003677°, Dec=69.679944°
- **Pixel Position:** x=388.7, y=513.5
- **SNR:** 422.8
- **Composite Score:** 0.601
- **Anomaly Score:** 0.655
- **Key Features:** SNR=422.8, ecc=1.07, asym=0.88
- **Flags:** high_ellipticity
- **Cutout:** ![Candidate #16](outputs/figures/cutouts/test_jwst_image_1_i2d_anomaly_457.png)

### Candidate #17

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F115W
- **Observation ID:** test_obs_1
- **Coordinates:** RA=149.058294°, Dec=69.681722°
- **Pixel Position:** x=199.1, y=531.5
- **SNR:** 304.9
- **Composite Score:** 0.600
- **Anomaly Score:** 0.690
- **Key Features:** SNR=304.9, ecc=8.95, asym=0.80
- **Flags:** high_ellipticity
- **Cutout:** ![Candidate #17](outputs/figures/cutouts/test_jwst_image_1_i2d_anomaly_475.png)

### Candidate #18

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F200W
- **Observation ID:** test_obs_2
- **Coordinates:** RA=149.003432°, Dec=69.684300°
- **Pixel Position:** x=389.6, y=557.1
- **SNR:** 350.7
- **Composite Score:** 0.597
- **Anomaly Score:** 0.675
- **Key Features:** SNR=350.7, ecc=1.00, asym=0.85
- **Flags:** high_ellipticity
- **Cutout:** ![Candidate #18](outputs/figures/cutouts/test_jwst_image_2_i2d_anomaly_469.png)

### Candidate #19

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F200W
- **Observation ID:** test_obs_2
- **Coordinates:** RA=149.050698°, Dec=69.685446°
- **Pixel Position:** x=225.5, y=568.7
- **SNR:** 350.0
- **Composite Score:** 0.579
- **Anomaly Score:** 0.586
- **Key Features:** SNR=350.0, ecc=0.00, asym=0.70
- **Cutout:** ![Candidate #19](outputs/figures/cutouts/test_jwst_image_2_i2d_anomaly_479.png)

### Candidate #20

- **Type:** image
- **Instrument:** NIRCAM
- **Filter:** F444W
- **Observation ID:** test_obs_3
- **Coordinates:** RA=148.948142°, Dec=69.650065°
- **Pixel Position:** x=581.7, y=214.7
- **SNR:** 231.9
- **Composite Score:** 0.578
- **Anomaly Score:** 0.620
- **Key Features:** SNR=231.9, ecc=0.39, asym=0.91
- **Cutout:** ![Candidate #20](outputs/figures/cutouts/test_jwst_image_3_i2d_anomaly_166.png)

## Verification Checklist

Before claiming any discovery, verify candidates using:

1. **Cross-filter verification:** Check if candidate appears in other filters
2. **Multi-epoch consistency:** Verify candidate persists across different observations
3. **Catalog cross-match:** Check against known catalogs (e.g., SIMBAD, Gaia)
4. **PSF analysis:** Verify candidate is not a diffraction spike or PSF artifact
5. **Cosmic ray check:** Examine multiple exposures to rule out cosmic rays
6. **Detection threshold sensitivity:** Re-run with different detection thresholds
7. **Independent method:** Verify using different source detection algorithms
8. **Photometric consistency:** Check if photometry is consistent across filters
9. **Morphology validation:** Verify unusual morphology is not due to blending
10. **WCS accuracy:** Verify astrometric solution is accurate for this region

## Reproducibility

This analysis can be reproduced by:

1. Installing dependencies: `pip install -r requirements.txt`
2. Configuring target in `config.yaml`
3. Running: `python run_pipeline.py`

**Configuration used:**
- Random seed: 42
- Detection threshold: 3.0 sigma
- Max observations: 20
- Max total size: 1.0 GB

## Output Files

All outputs are saved in the `outputs/` directory:

- `outputs/tables/download_manifest.csv` - List of downloaded files
- `outputs/tables/all_sources.csv` - All detected sources
- `outputs/tables/anomaly_candidates_images.csv` - Image anomaly candidates
- `outputs/tables/ranked_candidates.csv` - Ranked candidates (this report)
- `outputs/figures/cutouts/` - Source cutout images
- `outputs/figures/spectra/` - Spectrum plots (if spectra analyzed)
