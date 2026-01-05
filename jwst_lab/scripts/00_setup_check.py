#!/usr/bin/env python3
"""
Environment setup check for JWST Research Pipeline.
Validates that all required dependencies are installed and accessible.
"""

import sys
import importlib
from pathlib import Path

REQUIRED_PACKAGES = {
    'astroquery': 'astroquery',
    'astropy': 'astropy',
    'numpy': 'numpy',
    'pandas': 'pandas',
    'scipy': 'scipy',
    'skimage': 'skimage',  # scikit-image imports as skimage
    'photutils': 'photutils',
    'sep': 'sep',
    'matplotlib': 'matplotlib',
    'tqdm': 'tqdm',
    'yaml': 'yaml',  # pyyaml imports as yaml
    'rich': 'rich',
    'sklearn': 'sklearn',  # scikit-learn imports as sklearn
}

OPTIONAL_PACKAGES = {
    'reproject': 'reproject',
}


def check_package(package_name, import_name=None):
    """Check if a package can be imported."""
    if import_name is None:
        import_name = package_name
    
    try:
        importlib.import_module(import_name)
        return True, None
    except ImportError as e:
        return False, str(e)


def main():
    """Run environment checks."""
    print("=" * 60)
    print("JWST Research Pipeline - Environment Check")
    print("=" * 60)
    
    # Check Python version
    python_version = sys.version_info
    print(f"\nPython version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    if python_version < (3, 10):
        print("WARNING: Python 3.10+ recommended")
    
    # Check required packages
    print("\nChecking required packages...")
    all_ok = True
    for package_name, import_name in REQUIRED_PACKAGES.items():
        ok, error = check_package(package_name, import_name)
        if ok:
            try:
                mod = importlib.import_module(import_name)
                version = getattr(mod, '__version__', 'unknown')
                print(f"  ✓ {package_name:20s} (version {version})")
            except:
                print(f"  ✓ {package_name:20s} (installed)")
        else:
            print(f"  ✗ {package_name:20s} - MISSING")
            print(f"    Error: {error}")
            all_ok = False
    
    # Check optional packages
    print("\nChecking optional packages...")
    for package_name, import_name in OPTIONAL_PACKAGES.items():
        ok, error = check_package(package_name, import_name)
        if ok:
            try:
                mod = importlib.import_module(import_name)
                version = getattr(mod, '__version__', 'unknown')
                print(f"  ✓ {package_name:20s} (version {version})")
            except:
                print(f"  ✓ {package_name:20s} (installed)")
        else:
            print(f"  - {package_name:20s} - Not installed (optional)")
    
    # Check directory structure
    print("\nChecking directory structure...")
    base_dir = Path(__file__).parent.parent
    required_dirs = [
        'data/raw',
        'data/products',
        'outputs/figures/cutouts',
        'outputs/figures/spectra',
        'outputs/tables',
        'outputs/report',
    ]
    
    for dir_path in required_dirs:
        full_path = base_dir / dir_path
        if full_path.exists():
            print(f"  ✓ {dir_path}")
        else:
            print(f"  ✗ {dir_path} - MISSING")
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"    Created {dir_path}")
    
    # Final status
    print("\n" + "=" * 60)
    if all_ok:
        print("✓ All required packages are installed!")
        print("Environment is ready for JWST pipeline.")
        return 0
    else:
        print("✗ Some required packages are missing.")
        print("Please install them using: pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())

