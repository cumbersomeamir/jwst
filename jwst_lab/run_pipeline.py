#!/usr/bin/env python3
"""
Main pipeline runner: executes all steps in sequence.
"""

import sys
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

# Scripts to run in order
SCRIPTS = [
    ("00_setup_check.py", "Environment Check"),
    ("01_download_jwst.py", "Download JWST Data"),
    ("02_analyze_images.py", "Analyze Images"),
    ("03_analyze_spectra.py", "Analyze Spectra"),
    ("04_rank_candidates.py", "Rank Candidates"),
    ("05_make_report.py", "Generate Report"),
    ("06_verify_candidates.py", "Verify Candidates"),
]

def main():
    """Run the complete pipeline."""
    base_dir = Path(__file__).parent
    scripts_dir = base_dir / "scripts"
    
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]JWST Research Pipeline[/bold cyan]\n"
        "Anomaly Candidate Detection System",
        border_style="cyan"
    ))
    console.print("")
    
    for script_name, description in SCRIPTS:
        script_path = scripts_dir / script_name
        
        if not script_path.exists():
            console.print(f"[red]Error: Script not found: {script_path}[/red]")
            return 1
        
        console.print(f"\n[bold yellow]Step: {description}[/bold yellow]")
        console.print(f"Running: {script_name}")
        console.print("-" * 60)
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(base_dir),
                check=False
            )
            
            if result.returncode != 0:
                console.print(f"\n[red]✗ {description} failed with exit code {result.returncode}[/red]")
                
                # Some scripts can fail gracefully (e.g., no spectra found)
                if script_name == "03_analyze_spectra.py":
                    console.print("[yellow]Continuing (spectra analysis is optional)[/yellow]")
                    continue
                else:
                    console.print("[red]Pipeline stopped. Please check errors above.[/red]")
                    return 1
            else:
                console.print(f"[green]✓ {description} completed[/green]")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Pipeline interrupted by user[/yellow]")
            return 1
        except Exception as e:
            console.print(f"\n[red]Error running {script_name}: {e}[/red]")
            return 1
    
    # Final summary
    report_path = base_dir / "outputs" / "report" / "REPORT.md"
    
    console.print("\n")
    console.print(Panel.fit(
        f"[bold green]Pipeline Complete![/bold green]\n\n"
        f"Report generated at:\n[cyan]{report_path}[/cyan]\n\n"
        f"View all outputs in: [cyan]{base_dir / 'outputs'}[/cyan]",
        border_style="green"
    ))
    console.print("")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


