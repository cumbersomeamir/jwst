#!/usr/bin/env python3
"""
Analyze JWST images: detect sources, compute morphology, identify anomalies.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from scipy import ndimage
from scipy.stats import median_abs_deviation
from sklearn.ensemble import IsolationForest
import sep
from tqdm import tqdm
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils import load_config, ensure_dir

console = Console()


def load_science_array(fits_path):
    """Load the primary science array from a FITS file."""
    with fits.open(fits_path) as hdul:
        # Try to find the best science extension
        science_data = None
        wcs = None
        
        for hdu in hdul:
            if hdu.data is not None and hdu.data.ndim == 2:
                # Check if this is larger than what we have
                if science_data is None or hdu.data.size > science_data.size:
                    science_data = hdu.data.astype(float)
                    try:
                        wcs = WCS(hdu.header)
                    except:
                        wcs = None
        
        if science_data is None:
            # Fallback to primary HDU
            science_data = hdul[0].data.astype(float)
            try:
                wcs = WCS(hdul[0].header)
            except:
                wcs = None
        
        return science_data, wcs


def robust_background(data):
    """Estimate robust background using median and MAD."""
    # Use a subset for speed if image is very large
    if data.size > 10_000_000:
        sample = np.random.choice(data.flatten(), size=1_000_000, replace=False)
    else:
        sample = data.flatten()
    
    # Remove NaN and inf
    sample = sample[np.isfinite(sample)]
    
    if len(sample) == 0:
        return 0.0, 1.0
    
    median_bg = np.median(sample)
    mad_bg = median_abs_deviation(sample, scale='normal')
    
    return median_bg, mad_bg


def detect_sources(data, background, background_rms, threshold_sigma=3.0):
    """Detect sources using SEP or photutils."""
    # Subtract background
    data_sub = data - background
    
    # Run SEP detection
    try:
        objects = sep.extract(
            data_sub.astype(np.float64),
            threshold=threshold_sigma * background_rms,
            minarea=5,
            deblend_nthresh=32,
            deblend_cont=0.005,
            clean=True,
            clean_param=1.0
        )
        return objects
    except Exception as e:
        console.print(f"[yellow]Warning: SEP extraction failed: {e}, trying photutils fallback[/yellow]")
        # Fallback to photutils
        from photutils.detection import DAOStarFinder
        finder = DAOStarFinder(
            threshold=threshold_sigma * background_rms,
            fwhm=3.0
        )
        sources = finder(data_sub)
        if sources is None or len(sources) == 0:
            return None
        # Convert to SEP-like format
        objects = np.zeros(len(sources), dtype=[
            ('x', 'f8'), ('y', 'f8'), ('flux', 'f8'), ('fluxerr', 'f8'),
            ('peak', 'f8'), ('area', 'f8'), ('a', 'f8'), ('b', 'f8'),
            ('theta', 'f8'), ('cxx', 'f8'), ('cyy', 'f8'), ('cxy', 'f8'),
            ('kron_radius', 'f8'), ('flag', 'i4')
        ])
        objects['x'] = sources['xcentroid'].value if hasattr(sources['xcentroid'], 'value') else sources['xcentroid']
        objects['y'] = sources['ycentroid'].value if hasattr(sources['ycentroid'], 'value') else sources['ycentroid']
        if 'flux' in sources.colnames:
            objects['flux'] = sources['flux'].value if hasattr(sources['flux'], 'value') else sources['flux']
        else:
            objects['flux'] = sources['peak'].value if hasattr(sources['peak'], 'value') else sources['peak']
        objects['peak'] = sources['peak'].value if hasattr(sources['peak'], 'value') else sources['peak']
        if 'npix' in sources.colnames:
            objects['area'] = sources['npix'].value if hasattr(sources['npix'], 'value') else sources['npix']
        else:
            objects['area'] = np.ones(len(sources)) * 9
        return objects


def compute_morphology_metrics(data, x, y, background, background_rms, cutout_size=25):
    """Compute morphology metrics for a source."""
    h, w = data.shape
    x_int = int(round(x))
    y_int = int(round(y))
    
    # Extract cutout
    x0 = max(0, x_int - cutout_size)
    x1 = min(w, x_int + cutout_size)
    y0 = max(0, y_int - cutout_size)
    y1 = min(h, y_int + cutout_size)
    
    cutout = data[y0:y1, x0:x1].copy()
    cutout -= background
    
    # Local coordinates
    local_x = x - x0
    local_y = y - y0
    
    metrics = {}
    
    # Basic stats
    metrics['peak'] = np.nanmax(cutout)
    metrics['total_flux'] = np.nansum(cutout)
    metrics['mean_flux'] = np.nanmean(cutout)
    
    # SNR
    if background_rms > 0:
        metrics['snr'] = metrics['peak'] / background_rms
    else:
        metrics['snr'] = 0.0
    
    # Concentration (flux within different radii)
    r_pix = np.sqrt((np.arange(cutout.shape[0])[:, None] - local_y)**2 + 
                   (np.arange(cutout.shape[1])[None, :] - local_x)**2)
    if metrics['total_flux'] > 0:
        flux_r5 = np.nansum(cutout[r_pix <= 5])
        flux_r10 = np.nansum(cutout[r_pix <= 10])
        metrics['concentration'] = flux_r5 / flux_r10 if flux_r10 > 0 else 0.0
    else:
        metrics['concentration'] = 0.0
    
    # Asymmetry (simple measure)
    if cutout.size > 0:
        # Flip and subtract
        flipped = np.flipud(np.fliplr(cutout))
        asymmetry = np.nansum(np.abs(cutout - flipped)) / (2 * np.nansum(np.abs(cutout)) + 1e-10)
        metrics['asymmetry'] = asymmetry
    else:
        metrics['asymmetry'] = 0.0
    
    # Edge density (flux near edges of cutout)
    edge_mask = (r_pix > cutout_size * 0.7) & (r_pix < cutout_size * 0.9)
    if np.any(edge_mask):
        metrics['edge_density'] = np.nanmean(cutout[edge_mask])
    else:
        metrics['edge_density'] = 0.0
    
    # Eccentricity from moments
    if metrics['total_flux'] > 0:
        y_coords, x_coords = np.mgrid[0:cutout.shape[0], 0:cutout.shape[1]]
        y_coords = y_coords - local_y
        x_coords = x_coords - local_x
        
        m00 = np.nansum(cutout)
        m10 = np.nansum(x_coords * cutout)
        m01 = np.nansum(y_coords * cutout)
        m20 = np.nansum(x_coords**2 * cutout)
        m02 = np.nansum(y_coords**2 * cutout)
        m11 = np.nansum(x_coords * y_coords * cutout)
        
        # Centroid
        cx = m10 / m00
        cy = m01 / m00
        
        # Central moments
        mu20 = m20 / m00 - cx**2
        mu02 = m02 / m00 - cy**2
        mu11 = m11 / m00 - cx * cy
        
        # Eccentricity
        if mu20 + mu02 > 0:
            ecc = np.sqrt(1 - 4 * (mu20 * mu02 - mu11**2) / (mu20 + mu02)**2)
            metrics['eccentricity'] = ecc
        else:
            metrics['eccentricity'] = 0.0
    else:
        metrics['eccentricity'] = 0.0
    
    # Check for NaN/inf in cutout
    metrics['has_nan'] = np.any(~np.isfinite(cutout))
    
    return metrics


def flag_artifacts(row, data_shape, config):
    """Flag potential artifacts."""
    flags = []
    h, w = data_shape
    
    # Border check
    border_pix = config['analysis']['border_pixels']
    if (row['x'] < border_pix or row['x'] > w - border_pix or
        row['y'] < border_pix or row['y'] > h - border_pix):
        flags.append('border')
    
    # Ellipticity check
    if row.get('eccentricity', 0) > config['analysis']['max_ellipticity']:
        flags.append('high_ellipticity')
    
    # NaN check
    if row.get('has_nan', False):
        flags.append('has_nan')
    
    # Low SNR
    if row.get('snr', 0) < config['analysis']['min_snr']:
        flags.append('low_snr')
    
    return ';'.join(flags) if flags else 'none'


def create_cutout_plot(data, x, y, wcs, output_path, cutout_size=50):
    """Create cutout visualization with linear and log stretches."""
    h, w = data.shape
    x_int = int(round(x))
    y_int = int(round(y))
    
    x0 = max(0, x_int - cutout_size)
    x1 = min(w, x_int + cutout_size)
    y0 = max(0, y_int - cutout_size)
    y1 = min(h, y_int + cutout_size)
    
    cutout = data[y0:y1, x0:x1].copy()
    
    # Create figure with two subplots
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    
    # Linear stretch
    vmin = np.nanpercentile(cutout, 5)
    vmax = np.nanpercentile(cutout, 95)
    axes[0].imshow(cutout, origin='lower', cmap='gray', vmin=vmin, vmax=vmax)
    axes[0].plot(x - x0, y - y0, 'r+', markersize=15, markeredgewidth=2)
    axes[0].set_title('Linear Stretch')
    axes[0].axis('off')
    
    # Log stretch
    cutout_pos = cutout - np.nanmin(cutout) + 1e-10
    vmin_log = np.nanpercentile(cutout_pos, 5)
    vmax_log = np.nanpercentile(cutout_pos, 95)
    axes[1].imshow(np.log10(cutout_pos), origin='lower', cmap='gray', vmin=np.log10(vmin_log), vmax=np.log10(vmax_log))
    axes[1].plot(x - x0, y - y0, 'r+', markersize=15, markeredgewidth=2)
    axes[1].set_title('Log Stretch')
    axes[1].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def analyze_images():
    """Main image analysis function."""
    config = load_config()
    base_dir = Path(__file__).parent.parent
    
    # Load manifest
    manifest_path = base_dir / "outputs" / "tables" / "download_manifest.csv"
    if not manifest_path.exists():
        console.print("[red]No download manifest found. Please run 01_download_jwst.py first![/red]")
        return False
    
    manifest_df = pd.read_csv(manifest_path)
    
    # Filter for image products
    image_products = manifest_df[manifest_df['product_type'].isin(config['product_types_image'])]
    
    if len(image_products) == 0:
        console.print("[red]No image products found in manifest![/red]")
        return False
    
    console.print(f"\n[bold cyan]Analyzing {len(image_products)} image files[/bold cyan]")
    console.print("=" * 60)
    
    all_sources = []
    all_anomaly_candidates = []
    
    for idx, row in tqdm(image_products.iterrows(), total=len(image_products), desc="Processing images"):
        filepath = Path(row['file'])
        
        if not filepath.exists():
            console.print(f"[yellow]Warning: File not found: {filepath}[/yellow]")
            continue
        
        try:
            # Load data
            data, wcs = load_science_array(filepath)
            
            if data is None:
                console.print(f"[yellow]Warning: Could not load data from {filepath}[/yellow]")
                continue
            
            console.print(f"\nProcessing: {filepath.name}")
            console.print(f"  Shape: {data.shape}")
            
            # Background estimation
            background, background_rms = robust_background(data)
            console.print(f"  Background: {background:.2f} ± {background_rms:.2f}")
            
            # Source detection
            objects = detect_sources(data, background, background_rms, 
                                   threshold_sigma=config['analysis']['detection_threshold'])
            
            if objects is None or len(objects) == 0:
                console.print("  No sources detected")
                continue
            
            console.print(f"  Detected {len(objects)} sources")
            
            # Compute metrics for each source
            source_rows = []
            for obj in objects:
                # Handle both dict-like and structured array access
                try:
                    x = obj['x'] if isinstance(obj, dict) else obj['x']
                    y = obj['y'] if isinstance(obj, dict) else obj['y']
                except:
                    x = float(obj[0]) if hasattr(obj, '__getitem__') else 0.0
                    y = float(obj[1]) if hasattr(obj, '__getitem__') else 0.0
                
                # Get RA/Dec if WCS available
                ra, dec = None, None
                if wcs is not None:
                    try:
                        ra, dec = wcs.pixel_to_world_values(x, y)
                    except:
                        pass
                
                # Compute morphology
                metrics = compute_morphology_metrics(
                    data, x, y, background, background_rms,
                    cutout_size=config['analysis']['cutout_size']
                )
                
                # Get flux values safely
                try:
                    flux_val = obj['flux'] if isinstance(obj, dict) else obj['flux']
                    flux_err_val = obj['fluxerr'] if isinstance(obj, dict) else obj.get('fluxerr', np.nan) if hasattr(obj, 'get') else np.nan
                except:
                    flux_val = metrics['total_flux']
                    flux_err_val = np.nan
                
                source_row = {
                    'file': str(filepath),
                    'obs_id': row['obs_id'],
                    'instrument': row['instrument'],
                    'filter': row['filter'],
                    'x': float(x),
                    'y': float(y),
                    'ra': ra if ra is not None else np.nan,
                    'dec': dec if dec is not None else np.nan,
                    'flux': float(flux_val) if not np.isnan(flux_val) else np.nan,
                    'flux_err': float(flux_err_val) if not np.isnan(flux_err_val) else np.nan,
                    'peak': metrics['peak'],
                    'snr': metrics['snr'],
                    'concentration': metrics['concentration'],
                    'asymmetry': metrics['asymmetry'],
                    'edge_density': metrics['edge_density'],
                    'eccentricity': metrics['eccentricity'],
                    'has_nan': metrics['has_nan'],
                }
                
                # Flag artifacts
                source_row['flags'] = flag_artifacts(source_row, data.shape, config)
                
                source_rows.append(source_row)
            
            # Convert to DataFrame for this image
            image_sources_df = pd.DataFrame(source_rows)
            all_sources.append(image_sources_df)
            
            # Anomaly detection
            if len(image_sources_df) > 10:  # Need enough sources for anomaly detection
                # Select features for anomaly detection
                feature_cols = ['snr', 'concentration', 'asymmetry', 'edge_density', 'eccentricity']
                feature_data = image_sources_df[feature_cols].fillna(0).values
                
                # Remove infinite values
                feature_data = np.nan_to_num(feature_data, nan=0.0, posinf=0.0, neginf=0.0)
                
                # Isolation Forest
                iso_forest = IsolationForest(
                    contamination=config['analysis']['isolation_forest_contamination'],
                    random_state=config['random_seed']
                )
                anomaly_scores = iso_forest.fit_predict(feature_data)
                anomaly_scores_normalized = iso_forest.score_samples(feature_data)
                
                # Negative scores indicate anomalies (more negative = more anomalous)
                image_sources_df['anomaly_score'] = -anomaly_scores_normalized
                image_sources_df['is_anomaly'] = (anomaly_scores == -1)
                
                # Get top anomalies
                top_n = config['analysis']['top_anomalies_per_image']
                top_anomalies = image_sources_df.nlargest(top_n, 'anomaly_score')
                
                # Create cutouts for top anomalies
                cutouts_dir = base_dir / "outputs" / "figures" / "cutouts"
                ensure_dir(cutouts_dir)
                
                for anomaly_idx, anomaly_row in top_anomalies.iterrows():
                    cutout_filename = f"{filepath.stem}_anomaly_{int(anomaly_row.name)}.png"
                    cutout_path = cutouts_dir / cutout_filename
                    
                    create_cutout_plot(
                        data, anomaly_row['x'], anomaly_row['y'], wcs,
                        cutout_path,
                        cutout_size=config['analysis']['cutout_size']
                    )
                    
                    # Add to candidates
                    candidate_row = anomaly_row.copy()
                    candidate_row['cutout_path'] = str(cutout_path)
                    candidate_row['key_features'] = f"SNR={anomaly_row['snr']:.1f}, ecc={anomaly_row['eccentricity']:.2f}, asym={anomaly_row['asymmetry']:.2f}"
                    all_anomaly_candidates.append(candidate_row)
            
        except Exception as e:
            console.print(f"[red]Error processing {filepath}: {e}[/red]")
            import traceback
            traceback.print_exc()
            continue
    
    # Save all sources
    if all_sources:
        all_sources_df = pd.concat(all_sources, ignore_index=True)
        all_sources_path = base_dir / "outputs" / "tables" / "all_sources.csv"
        ensure_dir(all_sources_path.parent)
        all_sources_df.to_csv(all_sources_path, index=False)
        console.print(f"\n[green]✓ Saved {len(all_sources_df)} total sources to {all_sources_path}[/green]")
    
    # Save anomaly candidates
    if all_anomaly_candidates:
        candidates_df = pd.DataFrame(all_anomaly_candidates)
        candidates_path = base_dir / "outputs" / "tables" / "anomaly_candidates_images.csv"
        ensure_dir(candidates_path.parent)
        candidates_df.to_csv(candidates_path, index=False)
        console.print(f"[green]✓ Saved {len(candidates_df)} anomaly candidates to {candidates_path}[/green]")
    else:
        console.print("[yellow]No anomaly candidates found[/yellow]")
    
    return True


if __name__ == "__main__":
    success = analyze_images()
    sys.exit(0 if success else 1)


