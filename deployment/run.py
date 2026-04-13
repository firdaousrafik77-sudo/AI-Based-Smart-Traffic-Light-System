#!/usr/bin/env python3
"""Smart Traffic System Startup Script"""

import os
import sys
import subprocess
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).parent

def check_requirements():
    """Check if all requirements are installed"""
    print("Checking requirements...")
    reqs_file = PROJECT_ROOT / "backend" / "requirements.txt"
    
    try:
        import fastapi
        import uvicorn
        import numpy
        import pandas
        import sklearn
        print("✓ All basic requirements found")
        return True
    except ImportError as e:
        print(f"✗ Missing requirement: {e}")
        print(f"  Install with: pip install -r {reqs_file}")
        return False

def setup_env():
    """Setup environment variables"""
    env_file = PROJECT_ROOT / ".env"
    env_example = PROJECT_ROOT / ".env.example"
    
    if not env_file.exists():
        if env_example.exists():
            print(f"Creating .env file from template...")
            env_content = env_example.read_text()
            env_file.write_text(env_content)
            print(f"✓ Created {env_file}")
        else:
            print(f"Warning: Neither .env nor .env.example found")
    
    return str(env_file)

def run_server():
    """Run the server"""
    print("\n" + "=" * 60)
    print("🚦 Smart Traffic Control System")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        print("\nInstalling requirements...")
        reqs_file = PROJECT_ROOT / "backend" / "requirements.txt"
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(reqs_file)])
    
    # Setup environment
    env_file = setup_env()
    
    # Set Python path
    backend_path = str(PROJECT_ROOT / "backend")
    env = os.environ.copy()
    env["PYTHONPATH"] = backend_path
    
    # Get host from config
    try:
        sys.path.insert(0, backend_path)
        import config
        host = config.HOST
        port = config.PORT
    except ImportError:
        host = "localhost"
        port = 3000
    
    # Run the server
    print(f"\n✓ Starting backend server...")
    print(f"  Project root: {PROJECT_ROOT}")
    print(f"  Backend path: {backend_path}")
    print(f"  Environment: {env_file}")
    print(f"\n  Server will be available at: http://{host}:{port}")
    print(f"  API Docs: http://{host}:{port}/docs")
    print(f"  Frontend: http://{host}:{port}/")
    print("\n" + "=" * 60)
    
    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", host, "--port", str(port)],
            cwd=str(PROJECT_ROOT / "backend"),
            env=env
        )
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_server()
