#!/usr/bin/env python3
"""
Production Issue Diagnostic Script

Tests the most likely causes of the production 500 error:
1. Directory creation failures
2. Module import failures
3. Configuration issues
4. File permission issues
"""

import os
import sys
import traceback
from datetime import datetime

def test_directory_creation():
    """Test if we can create required directories."""
    print("🔍 Testing directory creation...")

    directories_to_test = [
        'data',
        'data/selections',
        'data/fixtures',
        'data/backups',
        'logs'
    ]

    results = {}

    for directory in directories_to_test:
        try:
            os.makedirs(directory, exist_ok=True)
            # Test write permissions
            test_file = os.path.join(directory, '.test_write')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            results[directory] = "✅ SUCCESS"
            print(f"   {directory}: ✅ Can create and write")
        except Exception as e:
            results[directory] = f"❌ FAILED: {e}"
            print(f"   {directory}: ❌ {e}")

    return results

def test_module_imports():
    """Test critical module imports."""
    print("\n🔍 Testing module imports...")

    modules_to_test = [
        ('data_manager', 'from data_manager import data_manager'),
        ('bbc_scraper', 'from bbc_scraper import BBCSportScraper'),
        ('config', 'from config import get_config'),
    ]

    results = {}

    for module_name, import_statement in modules_to_test:
        try:
            exec(import_statement)
            results[module_name] = "✅ SUCCESS"
            print(f"   {module_name}: ✅ Imported successfully")
        except Exception as e:
            results[module_name] = f"❌ FAILED: {e}"
            print(f"   {module_name}: ❌ {e}")
            print(f"      Traceback: {traceback.format_exc()}")

    return results

def test_configuration():
    """Test configuration loading."""
    print("\n🔍 Testing configuration...")

    try:
        from config import get_config
        config = get_config()

        print("   ✅ Configuration loaded successfully")
        print(f"   DEBUG: {config.DEBUG}")
        print(f"   LOG_LEVEL: {config.LOG_LEVEL}")
        print(f"   LOG_FILE: {config.LOG_FILE}")
        print(f"   ENABLE_BBC_SCRAPER: {config.ENABLE_BBC_SCRAPER}")
        print(f"   SECRET_KEY: {'Set' if config.SECRET_KEY else 'Not set'}")

        return {"status": "SUCCESS", "config": config}

    except Exception as e:
        print(f"   ❌ Configuration failed: {e}")
        return {"status": "FAILED", "error": str(e)}

def test_data_manager_initialization():
    """Test DataManager initialization specifically."""
    print("\n🔍 Testing DataManager initialization...")

    try:
        from data_manager import DataManager

        # Test with default path
        dm1 = DataManager()
        print("   ✅ DataManager initialized with default path")

        # Test directory creation
        print(f"   Base path: {dm1.base_path}")
        print(f"   Selections path: {dm1.selections_path}")
        print(f"   Fixtures path: {dm1.fixtures_path}")

        # Test basic operations
        try:
            stats = dm1.get_storage_stats()
            print(f"   ✅ Storage stats: {stats}")
        except Exception as e:
            print(f"   ⚠️ Storage stats failed: {e}")

        return {"status": "SUCCESS", "data_manager": dm1}

    except Exception as e:
        print(f"   ❌ DataManager initialization failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return {"status": "FAILED", "error": str(e)}

def test_bbc_scraper_initialization():
    """Test BBC scraper initialization."""
    print("\n🔍 Testing BBC scraper initialization...")

    try:
        from bbc_scraper import BBCSportScraper

        scraper = BBCSportScraper(rate_limit=2.0)
        print("   ✅ BBC scraper initialized successfully")
        print(f"   Rate limit: {scraper.rate_limit}")
        print(f"   Base URL: {scraper.BASE_URL}")

        return {"status": "SUCCESS", "scraper": scraper}

    except Exception as e:
        print(f"   ❌ BBC scraper initialization failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return {"status": "FAILED", "error": str(e)}

def test_admin_route_simulation():
    """Simulate the admin route logic to find where it fails."""
    print("\n🔍 Testing admin route simulation...")

    try:
        # Import required modules
        from data_manager import data_manager
        from bbc_scraper import BBCSportScraper
        from config import get_config

        print("   ✅ All imports successful for admin route")

        # Test data_manager availability
        if data_manager is None:
            print("   ❌ data_manager is None")
            return {"status": "FAILED", "error": "data_manager is None"}

        print("   ✅ data_manager is available")

        # Test BBC scraper availability
        if BBCSportScraper is None:
            print("   ❌ BBCSportScraper is None")
            return {"status": "FAILED", "error": "BBCSportScraper is None"}

        print("   ✅ BBCSportScraper is available")

        # Test getting current prediction week
        try:
            from app import get_current_prediction_week
            week = get_current_prediction_week()
            print(f"   ✅ Current prediction week: {week}")
        except Exception as e:
            print(f"   ❌ Failed to get prediction week: {e}")
            return {"status": "FAILED", "error": f"Prediction week failed: {e}"}

        # Test loading selections
        try:
            selections = data_manager.load_weekly_selections(week)
            print(f"   ✅ Loaded selections: {len(selections) if selections else 0} selections")
        except Exception as e:
            print(f"   ⚠️ Failed to load selections: {e}")

        return {"status": "SUCCESS"}

    except Exception as e:
        print(f"   ❌ Admin route simulation failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return {"status": "FAILED", "error": str(e)}

def main():
    """Run all diagnostic tests."""
    print("🚨 PRODUCTION ISSUE DIAGNOSTIC")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Current directory: {os.getcwd()}")
    print()

    # Run all tests
    results = {}

    results['directory_creation'] = test_directory_creation()
    results['module_imports'] = test_module_imports()
    results['configuration'] = test_configuration()
    results['data_manager'] = test_data_manager_initialization()
    results['bbc_scraper'] = test_bbc_scraper_initialization()
    results['admin_simulation'] = test_admin_route_simulation()

    # Summary
    print("\n📊 DIAGNOSTIC SUMMARY")
    print("=" * 50)

    failed_tests = []
    for test_name, result in results.items():
        if isinstance(result, dict) and result.get('status') == 'FAILED':
            failed_tests.append(test_name)
            print(f"❌ {test_name.upper()}: FAILED")
        else:
            print(f"✅ {test_name.upper()}: PASSED")

    print()
    if failed_tests:
        print("🚨 FAILED TESTS:")
        for test in failed_tests:
            print(f"   • {test}")
        print()
        print("💡 RECOMMENDED FIXES:")
        print("   1. Check file system permissions in production")
        print("   2. Ensure all required directories can be created")
        print("   3. Verify environment variables are set correctly")
        print("   4. Check Railway deployment logs for specific errors")
    else:
        print("✅ All diagnostic tests passed!")
        print("   The issue may be in the Railway deployment configuration")

    return results

if __name__ == "__main__":
    main()