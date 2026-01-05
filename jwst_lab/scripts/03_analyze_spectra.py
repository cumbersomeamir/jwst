#!/usr/bin/env python3
"""
Analyze JWST 1D spectra: detect lines, identify anomalies.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from astropy.io import fits
import matplotlib.pyplot as plt
from scipy import signal
from scipy.optimize import curve_fit
from tqdm import tqdm
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils import load_config, ensure_dir

console = Console()


def gaussian(x, amplitude, mean, stddev):
    """Gaussian function for line fitting."""
    return amplitude * np.exp(-((x - mean) / stddev) ** 2 / 2)


def smooth_spectrum(flux, window_size=5):
    """Smooth spectrum using moving average."""
    if window_size % 2 == 0:
        window_size += 1
    return signal.savgol_filter(flux, window_size, 3)


def detect_emission_lines(wavelength, flux, error, snr_threshold=3.0):
    """Detect emission lines in spectrum."""
    # Smooth continuum
    flux_smooth = smooth_spectrum(flux)
    continuum = flux_smooth
    
    # Subtract continuum
    flux_subtracted = flux - continuum
    
    # Compute SNR spectrum
    snr_spectrum = flux_subtracted / (error + 1e-10)
    
    # Find peaks
    peaks, properties = signal.find_peaks(
        snr_spectrum,
        height=snr_threshold,
        distance=5,
        prominence=snr_threshold
    )
    
    lines = []
    for peak_idx in peaks:
        # Fit Gaussian around peak
        fit_window = 20
        start_idx = max(0, peak_idx - fit_window)
        end_idx = min(len(wavelength), peak_idx + fit_window)
        
        wl_fit = wavelength[start_idx:end_idx]
        flux_fit = flux_subtracted[start_idx:end_idx]
        
        if len(wl_fit) < 5:
            continue
        
        try:
            # Initial guess
            p0 = [flux_subtracted[peak_idx], wavelength[peak_idx], 0.01]
            popt, _ = curve_fit(gaussian, wl_fit, flux_fit, p0=p0, maxfev=1000)
            
            # Compute equivalent width (simplified)
            line_flux = np.trapz(flux_fit, wl_fit)
            continuum_level = np.median(continuum[start_idx:end_idx])
            if continuum_level > 0:
                eq_width = line_flux / continuum_level
            else:
                eq_width = 0.0
            
            lines.append({
                'wavelength': popt[1],
                'amplitude': popt[0],
                'width': abs(popt[2]),
                'snr': snr_spectrum[peak_idx],
                'equivalent_width': eq_width,
                'peak_index': peak_idx,
            })
        except:
            # Fallback: simple peak properties
            lines.append({
                'wavelength': wavelength[peak_idx],
                'amplitude': flux_subtracted[peak_idx],
                'width': 0.01,
                'snr': snr_spectrum[peak_idx],
                'equivalent_width': 0.0,
                'peak_index': peak_idx,
            })
    
    return lines


def compute_spectrum_features(wavelength, flux, error, lines):
    """Compute features for anomaly detection."""
    features = {}
    
    # Continuum slope
    if len(wavelength) > 10:
        # Fit linear continuum
        coeffs = np.polyfit(wavelength, flux, 1)
        features['continuum_slope'] = coeffs[0]
    else:
        features['continuum_slope'] = 0.0
    
    # Mean flux
    features['mean_flux'] = np.nanmean(flux)
    
    # Flux variance
    features['flux_variance'] = np.nanvar(flux)
    
    # Number of lines
    features['n_lines'] = len(lines)
    
    # Mean line SNR
    if len(lines) > 0:
        features['mean_line_snr'] = np.mean([l['snr'] for l in lines])
        features['max_line_snr'] = np.max([l['snr'] for l in lines])
        features['total_line_flux'] = np.sum([l['amplitude'] for l in lines])
    else:
        features['mean_line_snr'] = 0.0
        features['max_line_snr'] = 0.0
        features['total_line_flux'] = 0.0
    
    # Wavelength coverage
    features['wavelength_range'] = np.max(wavelength) - np.min(wavelength)
    
    return features


def plot_spectrum(wavelength, flux, error, lines, output_path):
    """Create spectrum plot with detected lines."""
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    # Full spectrum
    axes[0].plot(wavelength, flux, 'b-', linewidth=0.5, label='Flux')
    axes[0].fill_between(wavelength, flux - error, flux + error, alpha=0.3, color='blue')
    
    # Mark detected lines
    for line in lines:
        axes[0].axvline(line['wavelength'], color='red', linestyle='--', alpha=0.7)
        axes[0].text(line['wavelength'], flux[line['peak_index']], 
                     f"  {line['wavelength']:.2f}", rotation=90, fontsize=8)
    
    axes[0].set_ylabel('Flux')
    axes[0].set_title('Spectrum with Detected Lines')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # SNR spectrum
    flux_smooth = smooth_spectrum(flux)
    flux_subtracted = flux - flux_smooth
    snr_spectrum = flux_subtracted / (error + 1e-10)
    
    axes[1].plot(wavelength, snr_spectrum, 'g-', linewidth=0.5)
    axes[1].axhline(3.0, color='red', linestyle='--', label='SNR threshold')
    axes[1].set_xlabel('Wavelength')
    axes[1].set_ylabel('SNR')
    axes[1].set_title('Signal-to-Noise Ratio')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def analyze_spectra():
    """Main spectra analysis function."""
    config = load_config()
    base_dir = Path(__file__).parent.parent
    
    # Check if spectra analysis is enabled
    if not config.get('product_types_spectra') or len(config['product_types_spectra']) == 0:
        console.print("[yellow]Spectra analysis disabled in config[/yellow]")
        return True
    
    # Load manifest
    manifest_path = base_dir / "outputs" / "tables" / "download_manifest.csv"
    if not manifest_path.exists():
        console.print("[red]No download manifest found. Please run 01_download_jwst.py first![/red]")
        return False
    
    manifest_df = pd.read_csv(manifest_path)
    
    # Filter for spectra products
    spectra_products = manifest_df[manifest_df['product_type'].isin(config['product_types_spectra'])]
    
    if len(spectra_products) == 0:
        console.print("[yellow]No spectra products found in manifest[/yellow]")
        return True  # Not an error, just no spectra
    
    console.print(f"\n[bold cyan]Analyzing {len(spectra_products)} spectra files[/bold cyan]")
    console.print("=" * 60)
    
    all_spectra_features = []
    all_lines = []
    
    for idx, row in tqdm(spectra_products.iterrows(), total=len(spectra_products), desc="Processing spectra"):
        filepath = Path(row['file'])
        
        if not filepath.exists():
            console.print(f"[yellow]Warning: File not found: {filepath}[/yellow]")
            continue
        
        try:
            with fits.open(filepath) as hdul:
                # Try to find wavelength and flux arrays
                wavelength = None
                flux = None
                error = None
                
                for hdu in hdul:
                    if hdu.data is not None:
                        # Check for 1D arrays
                        if hdu.data.ndim == 1:
                            # Try to identify from header or data shape
                            if wavelength is None:
                                wavelength = hdu.data
                            elif flux is None:
                                flux = hdu.data
                            elif error is None:
                                error = hdu.data
                
                # Alternative: check for table extensions
                if wavelength is None or flux is None:
                    for hdu in hdul:
                        if hasattr(hdu, 'data') and hasattr(hdu.data, 'columns'):
                            # Table HDU
                            cols = hdu.data.columns.names
                            if 'WAVELENGTH' in cols or 'WAVELENGTH' in [c.upper() for c in cols]:
                                wl_col = [c for c in cols if 'WAVELENGTH' in c.upper()][0]
                                wavelength = hdu.data[wl_col]
                            if 'FLUX' in cols or 'FLUX' in [c.upper() for c in cols]:
                                flux_col = [c for c in cols if 'FLUX' in c.upper()][0]
                                flux = hdu.data[flux_col]
                            if 'ERROR' in cols or 'ERROR' in [c.upper() for c in cols]:
                                err_col = [c for c in cols if 'ERROR' in c.upper()][0]
                                error = hdu.data[err_col]
                
                if wavelength is None or flux is None:
                    console.print(f"[yellow]Warning: Could not extract wavelength/flux from {filepath}[/yellow]")
                    continue
                
                # Ensure arrays are numpy arrays
                wavelength = np.array(wavelength)
                flux = np.array(flux)
                
                if error is None:
                    error = np.ones_like(flux) * np.nanstd(flux) * 0.1
                else:
                    error = np.array(error)
                
                # Remove NaN/inf
                valid = np.isfinite(wavelength) & np.isfinite(flux) & np.isfinite(error)
                wavelength = wavelength[valid]
                flux = flux[valid]
                error = error[valid]
                
                if len(wavelength) == 0:
                    console.print(f"[yellow]Warning: No valid data in {filepath}[/yellow]")
                    continue
                
                console.print(f"\nProcessing: {filepath.name}")
                console.print(f"  Wavelength range: {np.min(wavelength):.2f} - {np.max(wavelength):.2f}")
                
                # Detect lines
                lines = detect_emission_lines(wavelength, flux, error)
                console.print(f"  Detected {len(lines)} emission lines")
                
                # Compute features
                features = compute_spectrum_features(wavelength, flux, error, lines)
                
                # Save spectrum plot
                spectra_dir = base_dir / "outputs" / "figures" / "spectra"
                ensure_dir(spectra_dir)
                plot_path = spectra_dir / f"{filepath.stem}_spectrum.png"
                plot_spectrum(wavelength, flux, error, lines, plot_path)
                
                # Store results
                spectrum_row = {
                    'file': str(filepath),
                    'obs_id': row['obs_id'],
                    'instrument': row['instrument'],
                    'filter': row['filter'],
                    'wavelength_min': np.min(wavelength),
                    'wavelength_max': np.max(wavelength),
                    'plot_path': str(plot_path),
                    **features
                }
                all_spectra_features.append(spectrum_row)
                
                # Store individual lines
                for line in lines:
                    line_row = {
                        'file': str(filepath),
                        'obs_id': row['obs_id'],
                        'wavelength': line['wavelength'],
                        'amplitude': line['amplitude'],
                        'width': line['width'],
                        'snr': line['snr'],
                        'equivalent_width': line['equivalent_width'],
                    }
                    all_lines.append(line_row)
        
        except Exception as e:
            console.print(f"[red]Error processing {filepath}: {e}[/red]")
            import traceback
            traceback.print_exc()
            continue
    
    # Save results
    if all_spectra_features:
        spectra_df = pd.DataFrame(all_spectra_features)
        spectra_path = base_dir / "outputs" / "tables" / "spectra_features.csv"
        ensure_dir(spectra_path.parent)
        spectra_df.to_csv(spectra_path, index=False)
        console.print(f"\n[green]✓ Saved {len(spectra_df)} spectra to {spectra_path}[/green]")
    
    if all_lines:
        lines_df = pd.DataFrame(all_lines)
        lines_path = base_dir / "outputs" / "tables" / "spectra_lines.csv"
        ensure_dir(lines_path.parent)
        lines_df.to_csv(lines_path, index=False)
        console.print(f"[green]✓ Saved {len(lines_df)} emission lines to {lines_path}[/green]")
    
    # Anomaly detection on spectra (simple approach)
    if len(all_spectra_features) > 5:
        from sklearn.ensemble import IsolationForest
        
        spectra_df = pd.DataFrame(all_spectra_features)
        feature_cols = ['continuum_slope', 'mean_flux', 'n_lines', 'mean_line_snr', 'wavelength_range']
        feature_data = spectra_df[feature_cols].fillna(0).values
        feature_data = np.nan_to_num(feature_data, nan=0.0, posinf=0.0, neginf=0.0)
        
        iso_forest = IsolationForest(
            contamination=0.2,
            random_state=config['random_seed']
        )
        anomaly_scores = iso_forest.score_samples(feature_data)
        spectra_df['anomaly_score'] = -anomaly_scores
        
        # Save anomaly candidates
        candidates = spectra_df.nlargest(10, 'anomaly_score')
        candidates_path = base_dir / "outputs" / "tables" / "anomaly_candidates_spectra.csv"
        ensure_dir(candidates_path.parent)
        candidates.to_csv(candidates_path, index=False)
        console.print(f"[green]✓ Saved {len(candidates)} spectral anomaly candidates to {candidates_path}[/green]")
    
    return True


if __name__ == "__main__":
    success = analyze_spectra()
    sys.exit(0 if success else 1)


