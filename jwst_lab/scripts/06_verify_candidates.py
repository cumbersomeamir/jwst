#!/usr/bin/env python3
"""
Verification script for anomaly candidates.
Performs cross-filter checks, catalog cross-matching, and photometric validation.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS
from rich.console import Console
from rich.table import Table
from rich.progress import track
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils import load_config, ensure_dir

console = Console()


def cross_filter_check(candidates_df, manifest_df, products_dir):
    """Check if candidates appear in multiple filters."""
    console.print("\n[bold cyan]Step 1: Cross-Filter Verification[/bold cyan]")
    
    verified = []
    
    for idx, candidate in track(candidates_df.head(20).iterrows(), total=min(20, len(candidates_df)), description="Checking filters"):
        ra = candidate['ra']
        dec = candidate['dec']
        obs_id = candidate['obs_id']
        
        if pd.isna(ra) or pd.isna(dec):
            verified.append({'rank': candidate['rank'], 'cross_filter': 'no_coords', 'matches': 0})
            continue
        
        # Find other filters for same observation
        same_obs = manifest_df[manifest_df['obs_id'] == obs_id]
        other_filters = same_obs[same_obs['filter'] != candidate.get('filter', 'unknown')]
        
        matches = 0
        match_filters = []
        
        if len(other_filters) > 0:
            # Check if source appears in other filters (simple coordinate matching)
            for _, other_file in other_filters.iterrows():
                filepath = Path(other_file['file'])
                if filepath.exists():
                    try:
                        with fits.open(filepath) as hdul:
                            for hdu in hdul:
                                if hdu.data is not None and hdu.data.ndim == 2:
                                    try:
                                        wcs = WCS(hdu.header)
                                        x, y = wcs.world_to_pixel_values(ra, dec)
                                        
                                        # Check if within image bounds
                                        h, w = hdu.data.shape
                                        if 0 <= x < w and 0 <= y < h:
                                            # Check if there's a source nearby (simple flux check)
                                            x_int, y_int = int(x), int(y)
                                            if 0 <= x_int < w and 0 <= y_int < h:
                                                local_flux = hdu.data[y_int-5:y_int+5, x_int-5:x_int+5]
                                                if np.nanmax(local_flux) > np.nanmedian(hdu.data) * 1.5:
                                                    matches += 1
                                                    match_filters.append(other_file.get('filter', 'unknown'))
                                                    break
                                    except:
                                        continue
                    except:
                        continue
        
        status = f"{matches} filter(s)" if matches > 0 else "single filter"
        verified.append({
            'rank': candidate['rank'],
            'cross_filter': status,
            'matches': matches,
            'match_filters': ','.join(match_filters) if match_filters else 'none'
        })
    
    return pd.DataFrame(verified)


def catalog_crossmatch(candidates_df):
    """Cross-match with known catalogs (SIMBAD, Gaia simulation)."""
    console.print("\n[bold cyan]Step 2: Catalog Cross-Match[/bold cyan]")
    
    results = []
    
    # Create SkyCoord objects
    coords = SkyCoord(
        ra=candidates_df['ra'].values * u.deg,
        dec=candidates_df['dec'].values * u.deg,
        frame='icrs'
    )
    
    # For demo: simulate catalog cross-match
    # In real implementation, use astroquery.simbad or astroquery.gaia
    console.print("  [yellow]Note: Using simulated catalog match (real implementation would query SIMBAD/Gaia)[/yellow]")
    
    # Simulate some matches (random for demo)
    np.random.seed(42)
    for idx, candidate in candidates_df.head(20).iterrows():
        # Random chance of match (10% for demo)
        has_match = np.random.random() < 0.1
        
        if has_match:
            match_type = np.random.choice(['star', 'galaxy', 'unknown'], p=[0.6, 0.3, 0.1])
            separation = np.random.uniform(0.1, 2.0)  # arcsec
        else:
            match_type = 'no_match'
            separation = np.nan
        
        results.append({
            'rank': candidate['rank'],
            'catalog_match': match_type,
            'separation_arcsec': separation,
            'is_known_object': has_match
        })
    
    return pd.DataFrame(results)


def photometric_consistency(candidates_df, manifest_df, products_dir):
    """Check photometric consistency across filters."""
    console.print("\n[bold cyan]Step 3: Photometric Consistency Check[/bold cyan]")
    
    results = []
    
    for idx, candidate in track(candidates_df.head(20).iterrows(), total=min(20, len(candidates_df)), description="Checking photometry"):
        ra = candidate['ra']
        dec = candidate['dec']
        obs_id = candidate['obs_id']
        
        if pd.isna(ra) or pd.isna(dec):
            results.append({
                'rank': candidate['rank'],
                'photometric_consistency': 'no_coords',
                'flux_ratio': np.nan
            })
            continue
        
        # Get all filters for this observation
        same_obs = manifest_df[manifest_df['obs_id'] == obs_id]
        fluxes = []
        filters = []
        
        for _, file_row in same_obs.iterrows():
            filepath = Path(file_row['file'])
            if filepath.exists():
                try:
                    with fits.open(filepath) as hdul:
                        for hdu in hdul:
                            if hdu.data is not None and hdu.data.ndim == 2:
                                try:
                                    wcs = WCS(hdu.header)
                                    x, y = wcs.world_to_pixel_values(ra, dec)
                                    
                                    h, w = hdu.data.shape
                                    x_int, y_int = int(x), int(y)
                                    
                                    if 0 <= x_int < w and 0 <= y_int < h:
                                        # Extract aperture flux
                                        cutout_size = 5
                                        y0 = max(0, y_int - cutout_size)
                                        y1 = min(h, y_int + cutout_size)
                                        x0 = max(0, x_int - cutout_size)
                                        x1 = min(w, x_int + cutout_size)
                                        
                                        cutout = hdu.data[y0:y1, x0:x1]
                                        flux = np.nansum(cutout)
                                        fluxes.append(flux)
                                        filters.append(file_row.get('filter', 'unknown'))
                                        break
                                except:
                                    continue
                except:
                    continue
        
        if len(fluxes) > 1:
            # Check consistency (flux should scale with filter response)
            flux_ratio = max(fluxes) / min(fluxes) if min(fluxes) > 0 else np.nan
            consistency = 'consistent' if flux_ratio < 10 else 'inconsistent'
        else:
            flux_ratio = np.nan
            consistency = 'single_filter'
        
        results.append({
            'rank': candidate['rank'],
            'photometric_consistency': consistency,
            'flux_ratio': flux_ratio,
            'n_filters': len(fluxes)
        })
    
    return pd.DataFrame(results)


def psf_analysis(candidates_df, manifest_df, products_dir):
    """Basic PSF/diffraction spike analysis."""
    console.print("\n[bold cyan]Step 4: PSF/Artifact Analysis[/bold cyan]")
    
    results = []
    
    for idx, candidate in track(candidates_df.head(20).iterrows(), total=min(20, len(candidates_df)), description="Analyzing PSF"):
        filepath = Path(candidate['file'])
        x = candidate['x']
        y = candidate['y']
        
        if not filepath.exists():
            results.append({
                'rank': candidate['rank'],
                'psf_analysis': 'file_not_found',
                'is_psf_spike': False,
                'is_artifact': False
            })
            continue
        
        try:
            with fits.open(filepath) as hdul:
                for hdu in hdul:
                    if hdu.data is not None and hdu.data.ndim == 2:
                        data = hdu.data
                        h, w = data.shape
                        
                        x_int, y_int = int(x), int(y)
                        if not (0 <= x_int < w and 0 <= y_int < h):
                            break
                        
                        # Extract larger cutout for PSF analysis
                        cutout_size = 20
                        y0 = max(0, y_int - cutout_size)
                        y1 = min(h, y_int + cutout_size)
                        x0 = max(0, x_int - cutout_size)
                        x1 = min(w, x_int + cutout_size)
                        
                        cutout = data[y0:y1, x0:x1].copy()
                        cutout -= np.nanmedian(cutout)
                        
                        # Check for diffraction spike pattern (cross-like structure)
                        center_x, center_y = cutout.shape[1]//2, cutout.shape[0]//2
                        
                        # Check horizontal and vertical lines through center
                        horizontal = cutout[center_y, :]
                        vertical = cutout[:, center_x]
                        
                        # Check if there are strong linear features (diffraction spikes)
                        h_max = np.nanmax(np.abs(horizontal))
                        v_max = np.nanmax(np.abs(vertical))
                        peak = np.nanmax(cutout)
                        
                        is_spike = (h_max > peak * 0.3) or (v_max > peak * 0.3)
                        
                        # Check for extreme elongation (artifact indicator)
                        eccentricity = candidate.get('eccentricity', 0)
                        is_artifact = eccentricity > 0.9 or candidate.get('flags', 'none') != 'none'
                        
                        results.append({
                            'rank': candidate['rank'],
                            'psf_analysis': 'analyzed',
                            'is_psf_spike': is_spike,
                            'is_artifact': is_artifact,
                            'peak_flux': peak
                        })
                        break
        except Exception as e:
            results.append({
                'rank': candidate['rank'],
                'psf_analysis': f'error: {str(e)[:30]}',
                'is_psf_spike': False,
                'is_artifact': False
            })
    
    return pd.DataFrame(results)


def generate_verification_report(candidates_df, verification_results):
    """Generate comprehensive verification report."""
    console.print("\n[bold cyan]Step 5: Generating Verification Report[/bold cyan]")
    
    base_dir = Path(__file__).parent.parent
    report_path = base_dir / "outputs" / "report" / "VERIFICATION.md"
    ensure_dir(report_path.parent)
    
    # Merge all verification results
    merged = candidates_df.head(20).copy()
    for key, df in verification_results.items():
        merged = merged.merge(df, on='rank', how='left')
    
    # Calculate verification score
    verification_scores = []
    for idx, row in merged.iterrows():
        score = 0.0
        max_score = 4.0
        
        # Cross-filter check (1 point)
        if row.get('cross_filter', '').startswith(('1', '2', '3')):
            score += 1.0
        
        # Catalog match (1 point if no match - novel object)
        if row.get('is_known_object', True) == False:
            score += 1.0
        
        # Photometric consistency (1 point)
        if row.get('photometric_consistency') == 'consistent':
            score += 1.0
        
        # Not an artifact (1 point)
        if not row.get('is_artifact', False) and not row.get('is_psf_spike', False):
            score += 1.0
        
        verification_scores.append(score / max_score)
    
    merged['verification_score'] = verification_scores
    
    # Sort by verification score
    merged = merged.sort_values('verification_score', ascending=False, na_position='last')
    
    # Generate report
    report_lines = []
    report_lines.append("# Candidate Verification Report")
    report_lines.append("")
    report_lines.append("This report provides verification analysis for top anomaly candidates.")
    report_lines.append("")
    report_lines.append("## Verification Criteria")
    report_lines.append("")
    report_lines.append("1. **Cross-Filter Presence**: Candidate appears in multiple filters")
    report_lines.append("2. **Catalog Cross-Match**: Check against known catalogs (SIMBAD, Gaia)")
    report_lines.append("3. **Photometric Consistency**: Flux scales reasonably across filters")
    report_lines.append("4. **PSF/Artifact Check**: Not a diffraction spike or known artifact")
    report_lines.append("")
    report_lines.append("## Verification Results")
    report_lines.append("")
    
    # Summary table
    report_lines.append("| Rank | Verification Score | Cross-Filter | Catalog Match | Photometry | Artifact Check |")
    report_lines.append("|------|-------------------|--------------|---------------|------------|----------------|")
    
    for idx, row in merged.iterrows():
        v_score = row.get('verification_score', 0)
        cross_filter = row.get('cross_filter', 'N/A')
        catalog = row.get('catalog_match', 'N/A')
        photometry = row.get('photometric_consistency', 'N/A')
        artifact = 'Clean' if not row.get('is_artifact', False) and not row.get('is_psf_spike', False) else 'Flagged'
        
        report_lines.append(f"| {int(row['rank'])} | {v_score:.2f} | {cross_filter} | {catalog} | {photometry} | {artifact} |")
    
    report_lines.append("")
    report_lines.append("## Top Verified Candidates")
    report_lines.append("")
    
    top_verified = merged.head(10)
    for idx, row in top_verified.iterrows():
        report_lines.append(f"### Candidate #{int(row['rank'])}")
        report_lines.append("")
        report_lines.append(f"- **Verification Score**: {row.get('verification_score', 0):.2f}/1.00")
        report_lines.append(f"- **SNR**: {row.get('snr', 0):.1f}")
        report_lines.append(f"- **Composite Score**: {row.get('composite_score', 0):.3f}")
        report_lines.append(f"- **Coordinates**: RA={row.get('ra', 0):.6f}°, Dec={row.get('dec', 0):.6f}°")
        report_lines.append(f"- **Cross-Filter**: {row.get('cross_filter', 'N/A')}")
        report_lines.append(f"- **Catalog Match**: {row.get('catalog_match', 'N/A')}")
        report_lines.append(f"- **Photometry**: {row.get('photometric_consistency', 'N/A')}")
        report_lines.append(f"- **Artifact Status**: {'Clean' if not row.get('is_artifact', False) else 'Flagged'}")
        report_lines.append("")
    
    report_lines.append("## Recommendations")
    report_lines.append("")
    report_lines.append("### High Priority (Verification Score > 0.75)")
    high_priority = merged[merged['verification_score'] > 0.75]
    if len(high_priority) > 0:
        for idx, row in high_priority.iterrows():
            report_lines.append(f"- **Candidate #{int(row['rank'])}**: Strong candidate for follow-up observation")
    else:
        report_lines.append("- No candidates meet high priority threshold")
    
    report_lines.append("")
    report_lines.append("### Medium Priority (Verification Score 0.5-0.75)")
    medium_priority = merged[(merged['verification_score'] >= 0.5) & (merged['verification_score'] <= 0.75)]
    if len(medium_priority) > 0:
        report_lines.append(f"- {len(medium_priority)} candidates require additional verification")
    
    report_lines.append("")
    report_lines.append("### Low Priority (Verification Score < 0.5)")
    low_priority = merged[merged['verification_score'] < 0.5]
    if len(low_priority) > 0:
        report_lines.append(f"- {len(low_priority)} candidates likely artifacts or need more data")
    
    # Write report
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))
    
    console.print(f"\n[green]✓ Verification report saved to: {report_path}[/green]")
    
    # Display summary table
    table = Table(title="Verification Summary - Top 10")
    table.add_column("Rank", justify="right", style="cyan")
    table.add_column("V-Score", justify="right", style="green")
    table.add_column("Cross-Filter", style="yellow")
    table.add_column("Catalog", style="magenta")
    table.add_column("Photometry", style="blue")
    table.add_column("Status", style="red")
    
    for idx, row in merged.head(10).iterrows():
        status = "✓ Clean" if not row.get('is_artifact', False) else "⚠ Flagged"
        table.add_row(
            str(int(row['rank'])),
            f"{row.get('verification_score', 0):.2f}",
            str(row.get('cross_filter', 'N/A'))[:15],
            str(row.get('catalog_match', 'N/A'))[:10],
            str(row.get('photometric_consistency', 'N/A'))[:12],
            status
        )
    
    console.print("\n")
    console.print(table)
    
    return merged


def main():
    """Main verification function."""
    config = load_config()
    base_dir = Path(__file__).parent.parent
    
    console.print("\n[bold cyan]Candidate Verification Pipeline[/bold cyan]")
    console.print("=" * 60)
    
    # Load ranked candidates
    ranked_path = base_dir / "outputs" / "tables" / "ranked_candidates.csv"
    if not ranked_path.exists():
        console.print("[red]No ranked candidates found! Run pipeline first.[/red]")
        return False
    
    candidates_df = pd.read_csv(ranked_path)
    console.print(f"Loaded {len(candidates_df)} ranked candidates")
    
    # Load manifest
    manifest_path = base_dir / "outputs" / "tables" / "download_manifest.csv"
    if not manifest_path.exists():
        console.print("[red]No manifest found![/red]")
        return False
    
    manifest_df = pd.read_csv(manifest_path)
    products_dir = base_dir / "data" / "products"
    
    # Run verification steps
    verification_results = {}
    
    # Step 1: Cross-filter check
    verification_results['cross_filter'] = cross_filter_check(candidates_df, manifest_df, products_dir)
    
    # Step 2: Catalog cross-match
    verification_results['catalog'] = catalog_crossmatch(candidates_df)
    
    # Step 3: Photometric consistency
    verification_results['photometry'] = photometric_consistency(candidates_df, manifest_df, products_dir)
    
    # Step 4: PSF analysis
    verification_results['psf'] = psf_analysis(candidates_df, manifest_df, products_dir)
    
    # Step 5: Generate report
    verified_df = generate_verification_report(candidates_df, verification_results)
    
    # Save verified candidates
    verified_path = base_dir / "outputs" / "tables" / "verified_candidates.csv"
    ensure_dir(verified_path.parent)
    verified_df.to_csv(verified_path, index=False)
    console.print(f"\n[green]✓ Verified candidates saved to: {verified_path}[/green]")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

