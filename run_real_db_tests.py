#!/usr/bin/env python3
"""
Comprehensive test runner for real database integration tests.
Runs all tests with actual Django, LM Studio, and ChromaDB interactions.
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def check_prerequisites():
    """Check if all prerequisites are met for running real database tests."""
    print("🔍 Checking prerequisites...")
    
    # Set test-specific ChromaDB collection name to avoid deleting real data
    os.environ['CHROMA_COLLECTION_NAME'] = 'test_integration_collection'
    print("✅ Set CHROMA_COLLECTION_NAME for test isolation")
    
    # Check if Django settings module is set
    if not os.environ.get('DJANGO_SETTINGS_MODULE'):
        os.environ['DJANGO_SETTINGS_MODULE'] = 'research_tracker.settings'
        print("✅ Set DJANGO_SETTINGS_MODULE")
    
    # Check if LM Studio is running
    try:
        import requests
        response = requests.get("http://127.0.0.1:1234/v1/models", timeout=5)
        if response.status_code == 200:
            print("✅ LM Studio is running")
        else:
            print("❌ LM Studio is not responding correctly")
            return False
    except Exception as e:
        print(f"❌ LM Studio is not running or not accessible: {e}")
        print("Please start LM Studio with embedding model and run on http://127.0.0.1:1234/v1")
        return False
    
    # Check if ChromaDB directory exists and is writable
    chroma_path = Path("chroma_db")
    if chroma_path.exists():
        if not os.access(chroma_path, os.W_OK):
            print("❌ ChromaDB directory is not writable")
            return False
        print("✅ ChromaDB directory is accessible")
    else:
        print("✅ ChromaDB directory will be created")
    
    return True

def run_test_suite(test_type="all"):
    """Run the comprehensive test suite."""
    print(f"\n🚀 Running {test_type} real database integration tests...")
    
    test_commands = []
    
    if test_type in ["all", "api"]:
        test_commands.append([
            sys.executable, "-m", "pytest", 
            "core/test_comprehensive_api.py",
            "-v",
            "--tb=short",
            "--disable-warnings"
        ])
    
    if test_type in ["all", "views"]:
        test_commands.append([
            sys.executable, "-m", "pytest", 
            "core/test_views_real_db.py",
            "-v", 
            "--tb=short",
            "--disable-warnings"
        ])
    
    if test_type in ["all", "existing"]:
        test_commands.append([
            sys.executable, "-m", "pytest", 
            "core/tests.py",
            "-v",
            "--tb=short", 
            "--disable-warnings"
        ])
    
    all_passed = True
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n📋 Running test suite {i}/{len(test_commands)}")
        print(f"Command: {' '.join(cmd)}")
        print("-" * 60)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            if result.returncode == 0:
                print(f"✅ Test suite {i} PASSED")
            else:
                print(f"❌ Test suite {i} FAILED")
                all_passed = False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Test suite {i} TIMED OUT (5 minutes)")
            all_passed = False
        except Exception as e:
            print(f"💥 Test suite {i} ERROR: {e}")
            all_passed = False
    
    return all_passed

def cleanup_test_data():
    """Clean up any test data created during testing."""
    print("\n🧹 Cleaning up test data...")
    
    try:
        # Clean up ChromaDB test collections
        from core.chroma_client import get_chroma_client
        client = get_chroma_client()
        
        collections = client.list_collections()
        # Clean up test-specific collection and any other test collections
        test_collections = [c for c in collections if c.name.startswith("test_")]
        
        for collection in test_collections:
            try:
                client.delete_collection(collection.name)
                print(f"✅ Deleted test collection: {collection.name}")
            except Exception as e:
                print(f"⚠️ Could not delete collection {collection.name}: {e}")
                
    except Exception as e:
        print(f"⚠️ Could not cleanup ChromaDB: {e}")
    
    print("✅ Cleanup completed")

def run_with_prerequisites(test_type="all"):
    """Run tests with prerequisite checking and cleanup."""
    print("=" * 60)
    print("🧪 REAL DATABASE INTEGRATION TEST SUITE")
    print("=" * 60)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Exiting.")
        return False
    
    try:
        # Run tests
        success = run_test_suite(test_type)
        
        if success:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ API endpoints work correctly with real databases")
            print("✅ LM Studio integration is functioning")
            print("✅ ChromaDB persistence and deletion work")
            print("✅ Data consistency is maintained")
        else:
            print("\n💥 SOME TESTS FAILED!")
            print("❌ Check the output above for details")
        
        return success
        
    finally:
        # Always cleanup
        cleanup_test_data()

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run real database integration tests")
    parser.add_argument(
        "--type", 
        choices=["all", "api", "views", "existing"], 
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--no-cleanup", 
        action="store_true",
        help="Skip cleanup after tests (for debugging)"
    )
    
    args = parser.parse_args()
    
    if args.no_cleanup:
        # Override cleanup function
        global cleanup_test_data
        def cleanup_test_data():
            print("\n⏭️ Skipping cleanup as requested")
    
    success = run_with_prerequisites(args.type)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
