#!/usr/bin/env python3
"""
Test mode: Create sample FITS files for pipeline testing when MAST API is unavailable.
"""

import sys
import numpy as np
from pathlib import Path
from astropy.io import fits
from astropy.wcs import WCS
from astropy import units as u
from astropy.coordinates import SkyCoord
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils import load_config, ensure_dir

console = Console()

def create_test_fits(output_path, shape=(2048, 2048), n_sources=50):
    """Create a test FITS file with synthetic sources."""
    # Create WCS
    w = WCS(naxis=2)
    w.wcs.crpix = [shape[1]/2, shape[0]/2]
    w.wcs.crval = [148.968458, 69.679694]  # M82 coordinates
    w.wcs.cdelt = [-0.0001, 0.0001]  # ~0.036 arcsec/pixel
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    
    # Create base image with background
    data = np.random.normal(100, 10, shape).astype(np.float32)
    
    # Add some sources
    np.random.seed(42)
    for i in range(n_sources):
        x = np.random.uniform(100, shape[1]-100)
        y = np.random.uniform(100, shape[0]-100)
        flux = np.random.uniform(100, 1000)
        sigma = np.random.uniform(2, 5)
        
        # Create Gaussian source
        yy, xx = np.ogrid[:shape[0], :shape[1]]
        r2 = (xx - x)**2 + (yy - y)**2
        source = flux * np.exp(-r2 / (2 * sigma**2))
        data += source
    
    # Add a few "anomalous" sources
    for i in range(3):
        x = np.random.uniform(200, shape[1]-200)
        y = np.random.uniform(200, shape[0]-200)
        flux = np.random.uniform(2000, 5000)  # Brighter
        sigma = np.random.uniform(1, 2)  # More compact
        
        yy, xx = np.ogrid[:shape[0], :shape[1]]
        r2 = (xx - x)**2 + (yy - y)**2
        source = flux * np.exp(-r2 / (2 * sigma**2))
        data += source
    
    # Create FITS HDU
    hdu = fits.PrimaryHDU(data=data, header=w.to_header())
    hdu.header['INSTRUME'] = 'NIRCAM'
    hdu.header['FILTER'] = 'F115W'
    hdu.header['CALIB_LEVEL'] = 2
    
    # Write to file
    hdu.writeto(output_path, overwrite=True)
    return output_path

def main():
    """Create test data."""
    config = load_config()
    base_dir = Path(__file__).parent.parent
    products_dir = base_dir / "data" / "products"
    ensure_dir(products_dir)
    
    console.print("\n[bold yellow]TEST MODE: Creating sample FITS files[/bold yellow]")
    console.print("=" * 60)
    
    # Create 3 test images
    test_files = []
    for i in range(3):
        filename = f"test_jwst_image_{i+1}_i2d.fits"
        filepath = products_dir / filename
        create_test_fits(filepath, shape=(1024, 1024), n_sources=30 + i*10)
        test_files.append(filepath)
        console.print(f"Created: {filename} ({filepath.stat().st_size / 1024 / 1024:.1f} MB)")
    
    # Create manifest
    import pandas as pd
    manifest_rows = []
    for i, filepath in enumerate(test_files):
        manifest_rows.append({
            'file': str(filepath),
            'obs_id': f'test_obs_{i+1}',
            'instrument': 'NIRCAM',
            'filter': ['F115W', 'F200W', 'F444W'][i],
            'product_type': 'I2D',
            'calib_level': 2,
            'size_gb': filepath.stat().st_size / (1024 ** 3),
        })
    
    manifest_df = pd.DataFrame(manifest_rows)
    manifest_path = base_dir / "outputs" / "tables" / "download_manifest.csv"
    ensure_dir(manifest_path.parent)
    manifest_df.to_csv(manifest_path, index=False)
    
    console.print(f"\n[green]✓ Created {len(test_files)} test FITS files[/green]")
    console.print(f"✓ Manifest saved to: {manifest_path}")
    console.print("\n[yellow]Note: This is test data. For real JWST data, the MAST API must be working.[/yellow]")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

