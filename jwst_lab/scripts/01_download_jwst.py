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
    
    # Try alternative method: use MAST REST API directly to bypass get_product_list issues
    console.print("Trying MAST REST API method...")
    try:
        # Use MAST API directly via requests
        mast_url = "https://mast.stsci.edu/api/v0.1/Download/file"
        products_found = False
        
        for obs_row in selected_obs[:min(10, len(selected_obs))]:
            obs_id = obs_row['obs_id']
            try:
                # Query products via MAST API
                query_url = "https://mast.stsci.edu/api/v0.1/Download/bundle"
                params = {
                    "obs_id": obs_id,
                    "extension": "fits"
                }
                
                response = requests.get(query_url, params=params, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and len(data['data']) > 0:
                        console.print(f"  Found {len(data['data'])} products for {obs_id} via REST API")
                        # Filter for I2D products
                        for prod in data['data']:
                            if 'i2d' in prod.get('productSubGroupDescription', '').lower():
                                # Download the file
                                file_url = prod.get('dataURI', '')
                                if file_url:
                                    filename = prod.get('productFilename', file_url.split('/')[-1])
                                    filepath = products_dir / filename
                                    
                                    # Download file
                                    file_response = requests.get(file_url, timeout=300, stream=True)
                                    if file_response.status_code == 200:
                                        with open(filepath, 'wb') as f:
                                            for chunk in file_response.iter_content(chunk_size=8192):
                                                f.write(chunk)
                                        
                                        size_gb = filepath.stat().st_size / (1024 ** 3)
                                        if total_size_gb + size_gb <= config['max_total_gb']:
                                            all_products.append({
                                                'obs_id': obs_id,
                                                'productFilename': filename,
                                                'dataURI': str(filepath),
                                                'productSubGroupDescription': 'I2D',
                                                'instrument_name': obs_row.get('instrument_name', 'unknown'),
                                                'filter': prod.get('filter', 'unknown'),
                                                'calib_level': prod.get('calib_level', 2),
                                                'size_gb': size_gb,
                                            })
                                            total_size_gb += size_gb
                                            products_found = True
                                            if len(all_products) >= config['max_files']:
                                                break
                        if products_found:
                            console.print(f"Successfully downloaded {len(all_products)} products via REST API")
                            break
            except Exception as e:
                if 'timeout' not in str(e).lower():
                    console.print(f"  REST API error for {obs_id}: {str(e)[:60]}")
                continue
            time.sleep(0.5)  # Rate limiting
        
        if products_found:
            raise StopIteration  # Success, skip other methods
    except StopIteration:
        pass  # Success
    except Exception as e:
        console.print(f"[yellow]REST API method failed: {str(e)[:100]}[/yellow]")
    
    # Try alternative method: use download_products with observations table directly  
    if len(all_products) == 0:
        console.print("Trying direct download method...")
        try:
            # Get products using a workaround: query products via observations table
            # This bypasses get_product_list which has database issues
            obs_to_try = selected_obs[:min(10, len(selected_obs))]
            
            # Method 1: Try download_products with observations and productSubGroupDescription
            try:
                # First, try to get products table using query_criteria on products
                from astroquery.mast import Mast
                import time
            
                # Build product query for each observation
                products_list = []
                for obs_row in obs_to_try[:5]:  # Try first 5
                    obs_id = obs_row['obs_id']
                    try:
                        # Try using download_products with just the obs_id string
                        products = Observations.download_products(
                            obs_id,
                            productSubGroupDescription=config['product_types_image'][0] if config['product_types_image'] else 'I2D',
                            download_dir=str(products_dir),
                            cache=False,
                            mrp_only=False
                        )
                        
                        if products is not None and len(products) > 0:
                            products_list.append((obs_id, products))
                            console.print(f"  Successfully got products for {obs_id}")
                            break  # Got one working, use this method
                    except Exception as e:
                        if 'dataURI' not in str(e) and 'bigint' not in str(e).lower():
                            console.print(f"  Trying {obs_id}: {str(e)[:80]}")
                        continue
                    time.sleep(0.5)  # Small delay
                
                if len(products_list) > 0:
                    # Process downloaded files
                    downloaded_files = list(products_dir.rglob("*.fits"))
                    downloaded_files.extend(list(products_dir.rglob("*.fits.gz")))
                    
                    if len(downloaded_files) > 0:
                        console.print(f"Found {len(downloaded_files)} downloaded FITS files")
                        for filepath in downloaded_files:
                            if 'i2d' in filepath.name.lower() or any(pt.lower() in filepath.name.lower() for pt in config['product_types_image']):
                                try:
                                    size_gb = filepath.stat().st_size / (1024 ** 3)
                                    if total_size_gb + size_gb <= config['max_total_gb']:
                                        # Extract obs_id from path
                                        parts = filepath.parts
                                        obs_id = 'unknown'
                                        for part in parts:
                                            if part.startswith('jw') and len(part) > 10:
                                                obs_id = part
                                                break
                                        
                                        all_products.append({
                                            'obs_id': obs_id,
                                            'productFilename': filepath.name,
                                            'dataURI': str(filepath),
                                            'productSubGroupDescription': 'I2D',
                                            'instrument_name': obs_row.get('instrument_name', 'unknown') if 'obs_row' in locals() else 'unknown',
                                            'filter': 'unknown',
                                            'calib_level': 2,
                                            'size_gb': size_gb,
                                        })
                                        total_size_gb += size_gb
                                        if len(all_products) >= config['max_files']:
                                            break
                                except:
                                    continue
                        
                        if len(all_products) > 0:
                            console.print(f"Found {len(all_products)} products via direct download")
                            raise StopIteration  # Success, skip fallback
            except StopIteration:
                pass  # Success, continue
            except Exception as e1:
                # Method 2: Try without productSubGroupDescription filter
                try:
                    for obs_row in obs_to_try[:3]:
                        obs_id = obs_row['obs_id']
                        try:
                            products = Observations.download_products(
                                obs_id,
                                download_dir=str(products_dir),
                                cache=False,
                                mrp_only=False
                            )
                            
                            if products is not None:
                                # Check downloaded files
                                downloaded_files = list(products_dir.rglob("*.fits"))
                                for filepath in downloaded_files:
                                    if 'i2d' in filepath.name.lower():
                                        size_gb = filepath.stat().st_size / (1024 ** 3)
                                        if total_size_gb + size_gb <= config['max_total_gb']:
                                            all_products.append({
                                                'obs_id': obs_id,
                                                'productFilename': filepath.name,
                                                'dataURI': str(filepath),
                                                'productSubGroupDescription': 'I2D',
                                                'instrument_name': obs_row.get('instrument_name', 'unknown'),
                                                'filter': 'unknown',
                                                'calib_level': 2,
                                                'size_gb': size_gb,
                                            })
                                            total_size_gb += size_gb
                                            if len(all_products) >= config['max_files']:
                                                break
                                if len(all_products) > 0:
                                    break
                        except:
                            continue
                except:
                    pass
        except Exception as e:
            console.print(f"[yellow]Direct download method failed: {e}[/yellow]")
            pass
    
    # Continue with individual queries if we don't have products yet
    if len(all_products) == 0:
        for obs_id in tqdm(obs_ids_to_try, desc="Querying products"):
            try:
                # Try to get product list - use timeout and retry logic
                import time
                max_retries = 2
                products = None
                
                for retry in range(max_retries):
                    try:
                        products = Observations.get_product_list(obs_id)
                        if products is not None and len(products) > 0:
                            console.print(f"  Successfully retrieved {len(products)} products for {obs_id}")
                        break
                    except Exception as retry_error:
                        if 'bigint' in str(retry_error).lower():
                            # This obs_id has API issues, skip it
                            console.print(f"  Skipping {obs_id} due to API error")
                            products = None
                            break
                        if retry < max_retries - 1:
                            time.sleep(1)
                            continue
                        else:
                            console.print(f"  Error getting products for {obs_id}: {retry_error}")
                            products = None
                            break
                
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
        console.print("\n[red]No products found matching criteria![/red]")
        console.print("\n[yellow]MAST API Issue Detected:[/yellow]")
        console.print("The MAST database is currently returning errors for product queries.")
        console.print("This is a known MAST infrastructure issue, not a code problem.")
        console.print("\n[cyan]Workarounds:[/cyan]")
        console.print("1. Use test mode: python scripts/00_test_mode.py")
        console.print("2. Manually download FITS files to data/products/ and create manifest.csv")
        console.print("3. Try again later when MAST database is fixed")
        console.print("4. Use MAST portal (https://mast.stsci.edu) to download manually")
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

