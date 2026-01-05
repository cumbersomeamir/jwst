#!/usr/bin/env python3
"""
Generate final research report with top candidates and verification checklist.
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils import load_config, ensure_dir

console = Console()


def make_report():
    """Generate the final report."""
    config = load_config()
    base_dir = Path(__file__).parent.parent
    
    console.print("\n[bold cyan]Generating Research Report[/bold cyan]")
    console.print("=" * 60)
    
    # Load data
    manifest_path = base_dir / "outputs" / "tables" / "download_manifest.csv"
    ranked_path = base_dir / "outputs" / "tables" / "ranked_candidates.csv"
    
    if not manifest_path.exists():
        console.print("[red]No download manifest found![/red]")
        return False
    
    manifest_df = pd.read_csv(manifest_path)
    
    # Load ranked candidates
    if ranked_path.exists():
        ranked_df = pd.read_csv(ranked_path)
        top_20 = ranked_df.head(20)
    else:
        console.print("[yellow]No ranked candidates found, generating report with available data[/yellow]")
        top_20 = pd.DataFrame()
    
    # Generate report
    report_lines = []
    
    report_lines.append("# JWST Anomaly Candidate Research Report")
    report_lines.append("")
    report_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    
    # Executive Summary
    report_lines.append("## Executive Summary")
    report_lines.append("")
    report_lines.append("This report presents candidate anomalies identified in JWST public data.")
    report_lines.append("**Important:** These are candidate anomalies requiring verification.")
    report_lines.append("They should not be interpreted as 'never discovered before' without")
    report_lines.append("further cross-validation with other datasets and analysis methods.")
    report_lines.append("")
    
    # Data Summary
    report_lines.append("## Data Summary")
    report_lines.append("")
    report_lines.append(f"**Target:** {config['target_name']}")
    report_lines.append(f"**Mode:** {config['target_mode']}")
    report_lines.append("")
    report_lines.append("### Observations Downloaded")
    report_lines.append("")
    
    obs_summary = manifest_df.groupby(['obs_id', 'instrument']).agg({
        'file': 'count',
        'size_gb': 'sum'
    }).reset_index()
    obs_summary.columns = ['Observation ID', 'Instrument', 'Files', 'Size (GB)']
    
    report_lines.append("| Observation ID | Instrument | Files | Size (GB) |")
    report_lines.append("|----------------|------------|-------|-----------|")
    for _, row in obs_summary.iterrows():
        report_lines.append(f"| {row['Observation ID']} | {row['Instrument']} | {int(row['Files'])} | {row['Size (GB)']:.2f} |")
    report_lines.append("")
    
    report_lines.append("### Product Types")
    report_lines.append("")
    product_summary = manifest_df.groupby('product_type').agg({
        'file': 'count',
        'size_gb': 'sum'
    }).reset_index()
    product_summary.columns = ['Product Type', 'Count', 'Total Size (GB)']
    
    report_lines.append("| Product Type | Count | Total Size (GB) |")
    report_lines.append("|-------------|-------|-----------------|")
    for _, row in product_summary.iterrows():
        report_lines.append(f"| {row['Product Type']} | {int(row['Count'])} | {row['Total Size (GB)']:.2f} |")
    report_lines.append("")
    
    # Pipeline Steps
    report_lines.append("## Pipeline Steps")
    report_lines.append("")
    report_lines.append("1. **Data Download:** Queried MAST for JWST observations matching target criteria")
    report_lines.append("2. **Source Detection:** Used SEP/photutils for source extraction from I2D images")
    report_lines.append("3. **Morphology Analysis:** Computed metrics: SNR, concentration, asymmetry, eccentricity, edge density")
    report_lines.append("4. **Anomaly Detection:** Applied Isolation Forest on morphology features")
    report_lines.append("5. **Ranking:** Composite score based on anomaly score, SNR, artifact flags, cross-frame consistency")
    report_lines.append("")
    
    # Top Candidates
    report_lines.append("## Top 20 Anomaly Candidates")
    report_lines.append("")
    
    if len(top_20) > 0:
        report_lines.append("Candidates are ranked by composite score combining anomaly score, SNR,")
        report_lines.append("artifact flags, and cross-frame consistency.")
        report_lines.append("")
        
        for idx, row in top_20.iterrows():
            rank = int(row.get('rank', idx + 1))
            report_lines.append(f"### Candidate #{rank}")
            report_lines.append("")
            
            if 'source_type' in row:
                report_lines.append(f"- **Type:** {row['source_type']}")
            if 'instrument' in row and pd.notna(row['instrument']):
                report_lines.append(f"- **Instrument:** {row['instrument']}")
            if 'filter' in row and pd.notna(row['filter']):
                report_lines.append(f"- **Filter:** {row['filter']}")
            if 'obs_id' in row and pd.notna(row['obs_id']):
                report_lines.append(f"- **Observation ID:** {row['obs_id']}")
            if 'ra' in row and pd.notna(row['ra']):
                report_lines.append(f"- **Coordinates:** RA={row['ra']:.6f}°, Dec={row['dec']:.6f}°")
            if 'x' in row and pd.notna(row['x']):
                report_lines.append(f"- **Pixel Position:** x={row['x']:.1f}, y={row['y']:.1f}")
            if 'snr' in row and pd.notna(row['snr']):
                report_lines.append(f"- **SNR:** {row['snr']:.1f}")
            if 'composite_score' in row:
                report_lines.append(f"- **Composite Score:** {row['composite_score']:.3f}")
            if 'anomaly_score' in row:
                report_lines.append(f"- **Anomaly Score:** {row['anomaly_score']:.3f}")
            if 'key_features' in row and pd.notna(row['key_features']):
                report_lines.append(f"- **Key Features:** {row['key_features']}")
            if 'flags' in row and pd.notna(row['flags']) and row['flags'] != 'none':
                report_lines.append(f"- **Flags:** {row['flags']}")
            if 'cutout_path' in row and pd.notna(row['cutout_path']):
                cutout_rel = Path(row['cutout_path']).relative_to(base_dir)
                report_lines.append(f"- **Cutout:** ![Candidate #{rank}]({cutout_rel})")
            if 'plot_path' in row and pd.notna(row['plot_path']):
                plot_rel = Path(row['plot_path']).relative_to(base_dir)
                report_lines.append(f"- **Spectrum Plot:** ![Spectrum #{rank}]({plot_rel})")
            
            report_lines.append("")
    else:
        report_lines.append("No candidates found in this analysis.")
        report_lines.append("")
    
    # Verification Checklist
    report_lines.append("## Verification Checklist")
    report_lines.append("")
    report_lines.append("Before claiming any discovery, verify candidates using:")
    report_lines.append("")
    report_lines.append("1. **Cross-filter verification:** Check if candidate appears in other filters")
    report_lines.append("2. **Multi-epoch consistency:** Verify candidate persists across different observations")
    report_lines.append("3. **Catalog cross-match:** Check against known catalogs (e.g., SIMBAD, Gaia)")
    report_lines.append("4. **PSF analysis:** Verify candidate is not a diffraction spike or PSF artifact")
    report_lines.append("5. **Cosmic ray check:** Examine multiple exposures to rule out cosmic rays")
    report_lines.append("6. **Detection threshold sensitivity:** Re-run with different detection thresholds")
    report_lines.append("7. **Independent method:** Verify using different source detection algorithms")
    report_lines.append("8. **Photometric consistency:** Check if photometry is consistent across filters")
    report_lines.append("9. **Morphology validation:** Verify unusual morphology is not due to blending")
    report_lines.append("10. **WCS accuracy:** Verify astrometric solution is accurate for this region")
    report_lines.append("")
    
    # Reproducibility
    report_lines.append("## Reproducibility")
    report_lines.append("")
    report_lines.append("This analysis can be reproduced by:")
    report_lines.append("")
    report_lines.append("1. Installing dependencies: `pip install -r requirements.txt`")
    report_lines.append("2. Configuring target in `config.yaml`")
    report_lines.append("3. Running: `python run_pipeline.py`")
    report_lines.append("")
    report_lines.append(f"**Configuration used:**")
    report_lines.append(f"- Random seed: {config['random_seed']}")
    report_lines.append(f"- Detection threshold: {config['analysis']['detection_threshold']} sigma")
    report_lines.append(f"- Max observations: {config['max_obs']}")
    report_lines.append(f"- Max total size: {config['max_total_gb']} GB")
    report_lines.append("")
    
    # Output files
    report_lines.append("## Output Files")
    report_lines.append("")
    report_lines.append("All outputs are saved in the `outputs/` directory:")
    report_lines.append("")
    report_lines.append("- `outputs/tables/download_manifest.csv` - List of downloaded files")
    report_lines.append("- `outputs/tables/all_sources.csv` - All detected sources")
    report_lines.append("- `outputs/tables/anomaly_candidates_images.csv` - Image anomaly candidates")
    report_lines.append("- `outputs/tables/ranked_candidates.csv` - Ranked candidates (this report)")
    report_lines.append("- `outputs/figures/cutouts/` - Source cutout images")
    report_lines.append("- `outputs/figures/spectra/` - Spectrum plots (if spectra analyzed)")
    report_lines.append("")
    
    # Write report
    report_path = base_dir / "outputs" / "report" / "REPORT.md"
    ensure_dir(report_path.parent)
    
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))
    
    console.print(f"\n[green]✓ Report generated: {report_path}[/green]")
    
    return True


if __name__ == "__main__":
    success = make_report()
    sys.exit(0 if success else 1)


