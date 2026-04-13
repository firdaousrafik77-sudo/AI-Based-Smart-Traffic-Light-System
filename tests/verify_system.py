#!/usr/bin/env python3
"""System Verification Script - Check if all components are ready"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def check_imports():
    """Check if all required modules can be imported"""
    print("Checking imports...")
    
    imports_to_check = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'numpy': 'NumPy',
        'pandas': 'Pandas',
        'sklearn': 'Scikit-Learn',
        'pydantic': 'Pydantic',
        'websockets': 'WebSockets',
        'aiofiles': 'AioFiles',
        'dotenv': 'Python-DotEnv',
    }
    
    missing = []
    for module, name in imports_to_check.items():
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} - MISSING")
            missing.append(module)
    
    return len(missing) == 0, missing

def check_files():
    """Check if all required files exist"""
    print("\nChecking files...")
    
    files_to_check = {
        'backend/main.py': 'FastAPI Application',
        'backend/traffic_controller.py': 'Traffic Controller',
        'backend/ml_predictor.py': 'ML Predictor',
        'backend/optimization.py': 'Optimizers',
        'backend/database.py': 'Database Module',
        'backend/config.py': 'Configuration',
        'backend/requirements.txt': 'Requirements',
        'frontend/index.html': 'Frontend Dashboard',
        '.env': 'Environment Config',
    }
    
    missing = []
    for file_path, desc in files_to_check.items():
        full_path = Path(__file__).parent / file_path
        if full_path.exists():
            print(f"  ✓ {desc} ({file_path})")
        else:
            print(f"  ✗ {desc} ({file_path}) - MISSING")
            missing.append(file_path)
    
    return len(missing) == 0, missing

def check_backend_modules():
    """Check if backend modules can be imported"""
    print("\nChecking backend modules...")
    
    modules = {
        'traffic_controller.TrafficIntersection': 'Traffic Controller',
        'ml_predictor.TrafficPredictor': 'ML Predictor',
        'optimization.ReinforcementLearningOptimizer': 'RL Optimizer',
        'optimization.GeneticAlgorithmOptimizer': 'GA Optimizer',
        'database.TrafficDatabase': 'Database',
        'config': 'Config',
    }
    
    missing = []
    for module_path, desc in modules.items():
        try:
            parts = module_path.rsplit('.', 1)
            if len(parts) == 2:
                module_name, class_name = parts
                module = __import__(module_name)
                getattr(module, class_name)
            else:
                __import__(module_path)
            print(f"  ✓ {desc}")
        except (ImportError, AttributeError) as e:
            print(f"  ✗ {desc} - ERROR: {e}")
            missing.append(module_path)
    
    return len(missing) == 0, missing

def check_database():
    """Check if database can be initialized"""
    print("\nChecking database...")
    
    try:
        from database import TrafficDatabase
        db = TrafficDatabase()
        print(f"  ✓ Database initialized at {db.db_path}")
        return True, []
    except Exception as e:
        print(f"  ✗ Database error: {e}")
        return False, [str(e)]

def check_config():
    """Check if configuration loads"""
    print("\nChecking configuration...")
    
    try:
        import config
        print(f"  ✓ Host: {config.HOST}")
        print(f"  ✓ Port: {config.PORT}")
        print(f"  ✓ Log Level: {config.LOG_LEVEL}")
        print(f"  ✓ Database: {config.DB_PATH}")
        return True, []
    except Exception as e:
        print(f"  ✗ Configuration error: {e}")
        return False, [str(e)]

def main():
    """Run all checks"""
    print("=" * 60)
    print("🚦 Smart Traffic System - Verification")
    print("=" * 60 + "\n")
    
    all_good = True
    
    # Check imports
    imports_ok, missing_imports = check_imports()
    if not imports_ok:
        all_good = False
        print(f"\n⚠️  Missing packages: {', '.join(missing_imports)}")
        print(f"  Install with: pip install -r backend/requirements.txt\n")
    
    # Check files
    files_ok, missing_files = check_files()
    if not files_ok:
        all_good = False
        print(f"\n⚠️  Missing files: {', '.join(missing_files)}\n")
    
    # Check backend (only if imports are OK)
    if imports_ok:
        backend_ok, backend_errors = check_backend_modules()
        if not backend_ok:
            all_good = False
        
        # Check database (only if imports are OK)
        db_ok, db_errors = check_database()
        if not db_ok:
            all_good = False
        
        # Check config (only if imports are OK)
        cfg_ok, cfg_errors = check_config()
        if not cfg_ok:
            all_good = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_good:
        print("✅ System Check PASSED - Ready to run!")
        print("=" * 60)
        print("\nStart the system with:")
        print("  python run.py")
        print("\nThen access:")
        print("  http://localhost:3000/")
        return 0
    else:
        print("❌ System Check FAILED - Fix issues above")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
