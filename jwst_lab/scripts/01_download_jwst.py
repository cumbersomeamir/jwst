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
    
    selected_obs = jwst_obs[:config['max_obs']]
    console.print(f"Selecting top {len(selected_obs)} observations by exposure time")
    
    # Filter by instrument if specified
    if config.get('instruments_allowlist'):
        mask = np.array([inst in config['instruments_allowlist'] 
                        for inst in selected_obs['instrument_name']])
        selected_obs = selected_obs[mask]
        if len(selected_obs) == 0:
            console.print("[red]No observations match instrument filter![/red]")
            return False
    
    # Collect products
    all_products = []
    total_size_gb = 0.0
    
    console.print("\nCollecting product lists...")
    successful_obs = 0
    
    # Query products for each observation individually
    console.print("Querying products for each observation...")
    obs_ids_to_try = list(selected_obs['obs_id'])
    
    for obs_id in tqdm(obs_ids_to_try, desc="Querying products"):
        try:
            # Try to get product list - use timeout and retry logic
            import time
            max_retries = 2
            products = None
            
            for retry in range(max_retries):
                try:
                    products = Observations.get_product_list(obs_id)
                    break
                except Exception as retry_error:
                    if retry < max_retries - 1:
                        time.sleep(1)
                        continue
                    else:
                        raise retry_error
            
            if products is None or len(products) == 0:
                continue
            
            # Debug: show what product types we have
            if 'productSubGroupDescription' in products.colnames:
                unique_types = np.unique(products['productSubGroupDescription'])
                console.print(f"  Found product types: {list(unique_types)[:10]}")
            
            # Filter by product type
            product_mask = np.zeros(len(products), dtype=bool)
            for prod_type in config['product_types_image'] + config.get('product_types_spectra', []):
                try:
                    # Try direct match
                    try:
                        mask = products['productSubGroupDescription'] == prod_type
                        product_mask |= mask
                        if np.any(mask):
                            console.print(f"  Found {np.sum(mask)} products matching '{prod_type}'")
                    except:
                        # Try case-insensitive string matching
                        col_data = products['productSubGroupDescription']
                        mask = np.array([str(x).upper().strip() == prod_type.upper().strip() for x in col_data])
                        product_mask |= mask
                        if np.any(mask):
                            console.print(f"  Found {np.sum(mask)} products matching '{prod_type}' (case-insensitive)")
                except Exception as e:
                    continue
            
            # Filter by calib_level if available
            if 'calib_level' in products.colnames:
                try:
                    calib_vals = products['calib_level']
                    # Handle mixed types
                    calib_numeric = []
                    for v in calib_vals:
                        try:
                            calib_numeric.append(float(v) >= 2)
                        except:
                            calib_numeric.append(False)
                    product_mask &= np.array(calib_numeric)
                except:
                    pass
            
            if not np.any(product_mask):
                continue
            
            filtered_products = products[product_mask]
            
            # Add products to our list
            for prod in filtered_products:
                try:
                    size_gb = estimate_file_size(prod)
                    if total_size_gb + size_gb <= config['max_total_gb'] and len(all_products) < config['max_files']:
                        all_products.append({
                            'obs_id': obs_id,
                            'productFilename': str(prod.get('productFilename', '')),
                            'dataURI': str(prod.get('dataURI', '')),
                            'productSubGroupDescription': str(prod.get('productSubGroupDescription', '')),
                            'instrument_name': str(prod.get('instrument_name', '')),
                            'filter': str(prod.get('filter', '')),
                            'calib_level': prod.get('calib_level', 0),
                            'size_gb': size_gb,
                        })
                        total_size_gb += size_gb
                        
                        if len(all_products) >= config['max_files']:
                            break
                except Exception as e:
                    continue
            
            if len(all_products) >= config['max_files']:
                break
                
        except Exception as e:
            # Skip observations that fail
            continue
    
    # Check if we found any products
    if len(all_products) == 0:
        console.print("[red]No products found matching criteria![/red]")
        return False
    
    console.print(f"\nFound {len(all_products)} products to download")
    console.print(f"Estimated total size: {total_size_gb:.2f} GB")
    
    # Download products
    console.print("\nDownloading products...")
    manifest_rows = []
    
    # Group products by observation for batch download
    products_by_obs = defaultdict(list)
    for prod in all_products:
        products_by_obs[prod['obs_id']].append(prod)
    
    for obs_id, obs_products in tqdm(products_by_obs.items(), desc="Downloading"):
        try:
            # Get product list for this observation
            products_table = Observations.get_product_list(obs_id)
            
            # Filter to only the products we want
            product_filenames = [p['productFilename'] for p in obs_products]
            mask = np.array([fn in product_filenames for fn in products_table['productFilename']])
            products_to_download = products_table[mask]
            
            if len(products_to_download) == 0:
                continue
            
            # Download using astroquery's download_products
            manifest = Observations.download_products(
                products_to_download,
                download_dir=str(products_dir),
                cache=False
            )
            
            # Process downloaded files
            for prod_info in obs_products:
                filename = prod_info['productFilename']
                filepath = products_dir / "mastDownload" / "JWST" / obs_id / filename
                
                # Also check direct path
                if not filepath.exists():
                    filepath = products_dir / filename
                
                # Search recursively
                if not filepath.exists():
                    found_files = list(products_dir.rglob(filename))
                    if found_files:
                        filepath = found_files[0]
                
                if filepath.exists():
                    actual_size = filepath.stat().st_size / (1024 ** 3)
                    manifest_rows.append({
                        'file': str(filepath),
                        'obs_id': prod_info['obs_id'],
                        'instrument': prod_info['instrument_name'],
                        'filter': prod_info['filter'],
                        'product_type': prod_info['productSubGroupDescription'],
                        'calib_level': prod_info['calib_level'],
                        'size_gb': actual_size,
                    })
                else:
                    console.print(f"[yellow]Warning: File not found after download: {filename}[/yellow]")
                    
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to download products for {obs_id}: {e}[/yellow]")
            import traceback
            traceback.print_exc()
            continue
    
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

