#!/usr/bin/env python3
"""
Download JWST data from MAST using astroquery.
"""

import sys
import yaml
import pandas as pd
from pathlib import Path
from collections import defaultdict
from astroquery.mast import Observations
from tqdm import tqdm
import numpy as np
from rich.console import Console
from rich.table import Table
import requests
import json
import time

console = Console()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils import load_config, ensure_dir

def estimate_file_size(product_row):
    """Estimate file size in GB from product info."""
    # Try to get size from dataURI or file size if available
    size_bytes = product_row.get('size', 0)
    if size_bytes == 0:
        # Rough estimate: I2D files are typically 50-200 MB, X1D are smaller
        if 'I2D' in product_row.get('productSubGroupDescription', ''):
            size_bytes = 100 * 1024 * 1024  # 100 MB estimate
        else:
            size_bytes = 10 * 1024 * 1024  # 10 MB estimate
    return size_bytes / (1024 ** 3)  # Convert to GB


def download_jwst_data():
    """Main download function."""
    config = load_config()
    base_dir = Path(__file__).parent.parent
    products_dir = base_dir / "data" / "products"
    ensure_dir(products_dir)
    
    console.print("\n[bold cyan]JWST Data Download[/bold cyan]")
    console.print("=" * 60)
    
    # Query observations
    console.print(f"\nQuerying MAST for target: {config['target_name']}")
    
    if config['target_mode'] == 'object':
        obs_table = Observations.query_object(
            config['target_name'],
            radius=f"{config['radius_deg']}deg"
        )
    else:
        obs_table = Observations.query_region(
            coordinates=f"{config['ra_deg']} {config['dec_deg']}",
            radius=f"{config['radius_deg']}deg"
        )
    
    # Filter for JWST only
    jwst_obs = obs_table[obs_table['obs_collection'] == 'JWST']
    
    if len(jwst_obs) == 0:
        console.print("[red]No JWST observations found for this target![/red]")
        return False
    
    console.print(f"Found {len(jwst_obs)} JWST observations")
    
    # Sort by exposure time (descending) and take top N
    if 't_exptime' in jwst_obs.colnames:
        jwst_obs.sort('t_exptime', reverse=True)
    elif 't_min' in jwst_obs.colnames:
        jwst_obs.sort('t_min', reverse=True)
    elif 'obs_id' in jwst_obs.colnames:
        # Just take first N if no time column
        pass
    
    # Try more observations to find ones that are publicly accessible
    # Some observations may require authentication (401), so we'll try more
    selected_obs = jwst_obs[:min(config['max_obs'] * 3, len(jwst_obs))]  # Try 3x to find accessible ones
    console.print(f"Selecting top {len(selected_obs)} observations (will filter for accessible ones)")
    
    # Filter by instrument if specified
    if config.get('instruments_allowlist'):
        mask = np.array([inst in config['instruments_allowlist'] 
                        for inst in selected_obs['instrument_name']])
        selected_obs = selected_obs[mask]
        if len(selected_obs) == 0:
            console.print("[red]No observations match instrument filter![/red]")
            return False
    
    # NEW METHOD: Use dataURL from observations table directly
    # This bypasses get_product_list entirely which has database issues
    console.print("\n[bold green]Using dataURL from observations table (bypasses get_product_list)[/bold green]")
    
    all_products = []
    total_size_gb = 0.0
    
    for obs_row in tqdm(selected_obs, desc="Processing observations"):
        try:
            obs_id = obs_row['obs_id']
            data_url = obs_row.get('dataURL', '')
            instrument = obs_row.get('instrument_name', 'unknown')
            filter_name = obs_row.get('filters', 'unknown')
            
            # Check if this is an I2D product (from dataURL format: mast:JWST/product/..._i2d.fits)
            if not data_url or 'i2d' not in data_url.lower():
                # Not an I2D product, skip
                continue
            
            # Extract filename from dataURL (format: mast:JWST/product/filename.fits)
            if 'mast:' in data_url:
                filename = data_url.split('/')[-1]
            else:
                continue
            
            # Check if we want this product type
            product_type_match = False
            for prod_type in config['product_types_image']:
                if prod_type.lower() in data_url.lower():
                    product_type_match = True
                    break
            
            if not product_type_match:
                continue
            
            # Estimate size (I2D files are typically 50-200 MB)
            estimated_size_gb = 0.1  # Conservative 100 MB estimate
            
            if total_size_gb + estimated_size_gb > config['max_total_gb']:
                continue
            if len(all_products) >= config['max_files']:
                break
            
            # Use direct HTTP download (bypasses authentication issues with download_file)
            try:
                local_filepath = products_dir / filename
                
                # Check if file already exists (from previous partial download)
                if local_filepath.exists():
                    local_filepath.unlink()
                
                # Construct HTTP URL from MAST URI
                http_url = f"https://mast.stsci.edu/api/v0.1/Download/file?uri={data_url}"
                
                # Download using requests directly (works without authentication for public data)
                response = requests.get(http_url, timeout=300, stream=True)
                
                if response.status_code == 200:
                    # Stream download to handle large files
                    with open(local_filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    if local_filepath.exists() and local_filepath.stat().st_size > 0:
                        actual_size_gb = local_filepath.stat().st_size / (1024 ** 3)
                        
                        # Update total and add to list
                        if total_size_gb + actual_size_gb <= config['max_total_gb']:
                            all_products.append({
                                'obs_id': obs_id,
                                'productFilename': filename,
                                'dataURI': str(local_filepath),
                                'productSubGroupDescription': 'I2D',
                                'instrument_name': instrument,
                                'filter': filter_name if isinstance(filter_name, str) else str(filter_name),
                                'calib_level': obs_row.get('calib_level', 2),
                                'size_gb': actual_size_gb,
                            })
                            total_size_gb += actual_size_gb
                            console.print(f"  ✓ Downloaded {filename[:50]}... ({actual_size_gb:.3f} GB)")
                        else:
                            # File too large, remove it
                            local_filepath.unlink()
                            console.print(f"  ⚠ Skipped {filename[:50]}... (would exceed size limit)")
                    else:
                        console.print(f"  ✗ Download failed for {filename[:50]}... (file empty or not created)")
                elif response.status_code == 401:
                    # Not publicly available, skip silently
                    continue
                else:
                    console.print(f"  ✗ Download failed for {filename[:50]}... (HTTP {response.status_code})")
            except Exception as e:
                # Download failed, skip this observation
                error_str = str(e).lower()
                if 'timeout' not in error_str and 'connection' not in error_str:
                    console.print(f"  ✗ Exception downloading {obs_id[:50]}: {str(e)[:80]}")
                continue
                
        except Exception as e:
            continue
    
    # Check if we found any products
    if len(all_products) == 0:
        console.print("\n[red]No products found matching criteria![/red]")
        console.print("Tried to use dataURL from observations table but no I2D products found.")
        console.print("\n[cyan]Possible reasons:[/cyan]")
        console.print("1. No I2D products available for selected observations")
        console.print("2. All products exceed size limit")
        console.print("3. Download failures")
        return False
    
    console.print(f"\n[green]✓ Successfully downloaded {len(all_products)} products[/green]")
    console.print(f"Total size: {total_size_gb:.2f} GB")
    
    # Create manifest from downloaded products
    console.print("\nCreating manifest...")
    manifest_rows = []
    
    for prod_info in all_products:
        filepath = Path(prod_info['dataURI'])
        if filepath.exists():
            manifest_rows.append({
                'file': str(filepath),
                'obs_id': prod_info['obs_id'],
                'instrument': prod_info['instrument_name'],
                'filter': prod_info['filter'],
                'product_type': prod_info['productSubGroupDescription'],
                'calib_level': prod_info['calib_level'],
                'size_gb': prod_info['size_gb'],
            })
        else:
            console.print(f"[yellow]Warning: File not found: {filepath}[/yellow]")
    
    if len(manifest_rows) == 0:
        console.print("[red]No files were successfully downloaded![/red]")
        return False
    
    # Save manifest
    manifest_df = pd.DataFrame(manifest_rows)
    manifest_path = base_dir / "outputs" / "tables" / "download_manifest.csv"
    ensure_dir(manifest_path.parent)
    manifest_df.to_csv(manifest_path, index=False)
    
    console.print(f"\n[green]✓ Downloaded {len(manifest_rows)} files[/green]")
    console.print(f"Manifest saved to: {manifest_path}")
    
    # Print summary table
    table = Table(title="Download Summary")
    table.add_column("Instrument", style="cyan")
    table.add_column("Product Type", style="magenta")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Total Size (GB)", justify="right", style="yellow")
    
    summary = manifest_df.groupby(['instrument', 'product_type']).agg({
        'file': 'count',
        'size_gb': 'sum'
    }).reset_index()
    
    for _, row in summary.iterrows():
        table.add_row(
            row['instrument'],
            row['product_type'],
            str(int(row['file'])),
            f"{row['size_gb']:.2f}"
        )
    
    console.print("\n")
    console.print(table)
    
    return True


if __name__ == "__main__":
    success = download_jwst_data()
    sys.exit(0 if success else 1)

