#!/usr/bin/env python3
"""
Rank and combine anomaly candidates from images and spectra.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils import load_config, ensure_dir

console = Console()


def rank_candidates():
    """Main ranking function."""
    config = load_config()
    base_dir = Path(__file__).parent.parent
    
    console.print("\n[bold cyan]Ranking Anomaly Candidates[/bold cyan]")
    console.print("=" * 60)
    
    all_candidates = []
    
    # Load image candidates
    image_candidates_path = base_dir / "outputs" / "tables" / "anomaly_candidates_images.csv"
    if image_candidates_path.exists():
        image_candidates = pd.read_csv(image_candidates_path)
        image_candidates['source_type'] = 'image'
        all_candidates.append(image_candidates)
        console.print(f"Loaded {len(image_candidates)} image candidates")
    else:
        console.print("[yellow]No image candidates found[/yellow]")
    
    # Load spectra candidates
    spectra_candidates_path = base_dir / "outputs" / "tables" / "anomaly_candidates_spectra.csv"
    if spectra_candidates_path.exists():
        spectra_candidates = pd.read_csv(spectra_candidates_path)
        spectra_candidates['source_type'] = 'spectrum'
        all_candidates.append(spectra_candidates)
        console.print(f"Loaded {len(spectra_candidates)} spectra candidates")
    else:
        console.print("[yellow]No spectra candidates found[/yellow]")
    
    if len(all_candidates) == 0:
        console.print("[red]No candidates found to rank![/red]")
        return False
    
    # Combine
    combined = pd.concat(all_candidates, ignore_index=True, sort=False)
    
    # Normalize anomaly scores (higher is more anomalous)
    if 'anomaly_score' in combined.columns:
        # Ensure anomaly_score is numeric
        combined['anomaly_score'] = pd.to_numeric(combined['anomaly_score'], errors='coerce')
        combined['anomaly_score'] = combined['anomaly_score'].fillna(0)
        
        # Normalize to 0-1 range
        if combined['anomaly_score'].max() > combined['anomaly_score'].min():
            combined['anomaly_score_norm'] = (
                (combined['anomaly_score'] - combined['anomaly_score'].min()) /
                (combined['anomaly_score'].max() - combined['anomaly_score'].min())
            )
        else:
            combined['anomaly_score_norm'] = 0.5
    else:
        combined['anomaly_score_norm'] = 0.0
    
    # Compute composite score
    # Factors:
    # - High anomaly score (weight: 0.4)
    # - High SNR (weight: 0.3)
    # - Not flagged as artifact (weight: 0.2)
    # - Repeats across frames (weight: 0.1)
    
    composite_scores = np.zeros(len(combined))
    
    # Anomaly score component
    composite_scores += 0.4 * combined['anomaly_score_norm'].fillna(0).values
    
    # SNR component (normalize)
    if 'snr' in combined.columns:
        snr = pd.to_numeric(combined['snr'], errors='coerce').fillna(0)
        if snr.max() > snr.min():
            snr_norm = (snr - snr.min()) / (snr.max() - snr.min())
        else:
            snr_norm = snr * 0
        composite_scores += 0.3 * snr_norm.values
    elif 'max_line_snr' in combined.columns:
        # For spectra
        snr = pd.to_numeric(combined['max_line_snr'], errors='coerce').fillna(0)
        if snr.max() > snr.min():
            snr_norm = (snr - snr.min()) / (snr.max() - snr.min())
        else:
            snr_norm = snr * 0
        composite_scores += 0.3 * snr_norm.values
    
    # Artifact flag component (penalize flagged sources)
    if 'flags' in combined.columns:
        is_artifact = combined['flags'].fillna('').str.contains('border|high_ellipticity|has_nan|low_snr', case=False, na=False)
        composite_scores += 0.2 * (~is_artifact).astype(float).values
    else:
        composite_scores += 0.2  # Assume not artifact if no flags
    
    # Cross-frame consistency (check if same obs_id appears multiple times)
    if 'obs_id' in combined.columns:
        obs_counts = combined['obs_id'].value_counts()
        consistency = combined['obs_id'].map(obs_counts) / obs_counts.max()
        composite_scores += 0.1 * consistency.fillna(0).values
    else:
        composite_scores += 0.1
    
    combined['composite_score'] = composite_scores
    
    # Sort by composite score
    combined = combined.sort_values('composite_score', ascending=False, na_last=True)
    
    # Add rank
    combined['rank'] = range(1, len(combined) + 1)
    
    # Select columns for output
    output_cols = ['rank', 'composite_score', 'anomaly_score', 'source_type']
    
    if 'file' in combined.columns:
        output_cols.append('file')
    if 'obs_id' in combined.columns:
        output_cols.append('obs_id')
    if 'instrument' in combined.columns:
        output_cols.append('instrument')
    if 'filter' in combined.columns:
        output_cols.append('filter')
    if 'ra' in combined.columns:
        output_cols.extend(['ra', 'dec'])
    if 'x' in combined.columns:
        output_cols.extend(['x', 'y'])
    if 'snr' in combined.columns:
        output_cols.append('snr')
    if 'flags' in combined.columns:
        output_cols.append('flags')
    if 'key_features' in combined.columns:
        output_cols.append('key_features')
    if 'cutout_path' in combined.columns:
        output_cols.append('cutout_path')
    if 'plot_path' in combined.columns:
        output_cols.append('plot_path')
    
    # Add any remaining columns
    for col in combined.columns:
        if col not in output_cols:
            output_cols.append(col)
    
    ranked = combined[[c for c in output_cols if c in combined.columns]]
    
    # Save ranked candidates
    output_path = base_dir / "outputs" / "tables" / "ranked_candidates.csv"
    ensure_dir(output_path.parent)
    ranked.to_csv(output_path, index=False)
    
    console.print(f"\n[green]✓ Ranked {len(ranked)} candidates[/green]")
    console.print(f"Saved to: {output_path}")
    
    # Display top 10
    top_10 = ranked.head(10)
    table = Table(title="Top 10 Anomaly Candidates")
    table.add_column("Rank", justify="right", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Score", justify="right", style="green")
    table.add_column("SNR", justify="right", style="yellow")
    table.add_column("Instrument", style="blue")
    table.add_column("Flags", style="red")
    
    for _, row in top_10.iterrows():
        table.add_row(
            str(int(row['rank'])),
            row.get('source_type', 'unknown'),
            f"{row.get('composite_score', 0):.3f}",
            f"{row.get('snr', row.get('max_line_snr', 0)):.1f}" if 'snr' in row or 'max_line_snr' in row else "N/A",
            str(row.get('instrument', 'N/A')),
            str(row.get('flags', 'none'))[:30]
        )
    
    console.print("\n")
    console.print(table)
    
    return True


if __name__ == "__main__":
    success = rank_candidates()
    sys.exit(0 if success else 1)

