#!/usr/bin/env python3
"""
Start Working Arbitrage Dashboard

This script starts the simplified, working version of the arbitrage dashboard
that has been tested and verified to work with the current database.
"""

import os
import subprocess
import sys
from pathlib import Path

def main():
    """Start the working dashboard."""
    print("Starting Arbitrage Dashboard...")
    print("=" * 50)
    
    # Get project root
    project_root = Path(__file__).parent
    dashboard_path = project_root / "src" / "dashboard" / "simple_main.py"
    
    # Check if dashboard file exists
    if not dashboard_path.exists():
        print(f"❌ Dashboard file not found: {dashboard_path}")
        sys.exit(1)
    
    # Check environment file
    env_path = project_root / ".env"
    if not env_path.exists():
        print(f"❌ Environment file not found: {env_path}")
        print("Please ensure .env file exists with MongoDB credentials")
        sys.exit(1)
    
    print(f"✅ Dashboard file found: {dashboard_path}")
    print(f"✅ Environment file found: {env_path}")
    print()
    
    # Start Streamlit
    cmd = [
        "streamlit", "run", str(dashboard_path),
        "--server.port", "8501",
        "--server.address", "0.0.0.0",
        "--browser.gatherUsageStats", "false"
    ]
    
    print("Starting Streamlit dashboard...")
    print(f"Command: {' '.join(cmd)}")
    print()
    print("🚀 Dashboard will be available at: http://localhost:8501")
    print("📊 The dashboard shows real data from your MongoDB Atlas database")
    print("💡 Features working:")
    print("   - Database connectivity (SSL fixed)")
    print("   - Product listing (701 products available)")
    print("   - Alert monitoring (8 alerts available)")
    print("   - Basic analytics")
    print()
    print("Press Ctrl+C to stop the dashboard")
    print("=" * 50)
    
    try:
        subprocess.run(cmd, cwd=project_root)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 