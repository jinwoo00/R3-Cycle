#!/usr/bin/env python3
"""
Test Runner - Runs all R3-Cycle Raspberry Pi tests
Executes all test scripts and provides summary

Usage: python3 run_all_tests.py
       sudo python3 run_all_tests.py  (for hardware tests)
"""

import sys
import os
import subprocess
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Test definitions
TESTS = [
    {
        "name": "API Connectivity",
        "file": "test_api.py",
        "requires_sudo": False,
        "requires_hardware": False,
        "description": "Tests backend server connectivity"
    },
    {
        "name": "LCD Display",
        "file": "test_lcd.py",
        "requires_sudo": True,
        "requires_hardware": True,
        "description": "Tests I2C LCD display"
    },
    {
        "name": "RFID Reader",
        "file": "test_rfid.py",
        "requires_sudo": True,
        "requires_hardware": True,
        "description": "Tests RC522 RFID card reader"
    },
    {
        "name": "Load Cell",
        "file": "test_loadcell.py",
        "requires_sudo": True,
        "requires_hardware": True,
        "description": "Tests HX711 load cell & calibration"
    },
    {
        "name": "IR Sensor",
        "file": "test_ir_sensor.py",
        "requires_sudo": True,
        "requires_hardware": True,
        "description": "Tests IR obstacle sensor"
    },
    {
        "name": "Inductive Sensor",
        "file": "test_inductive.py",
        "requires_sudo": True,
        "requires_hardware": True,
        "description": "Tests inductive proximity sensor"
    },
    {
        "name": "Offline Mode",
        "file": "test_offline_mode.py",
        "requires_sudo": False,
        "requires_hardware": False,
        "description": "Tests offline mode database & sync"
    }
]

def print_header():
    """Print test runner header"""
    print("=" * 70)
    print(" " * 15 + "R3-CYCLE TEST SUITE RUNNER")
    print("=" * 70)
    print()

def print_test_header(test_info, test_num, total):
    """Print individual test header"""
    print()
    print("=" * 70)
    print(f" TEST {test_num}/{total}: {test_info['name']}")
    print("=" * 70)
    print(f" Description: {test_info['description']}")
    if test_info['requires_sudo']:
        print(" Note: Requires sudo for GPIO/I2C/SPI access")
    if test_info['requires_hardware']:
        print(" Note: Requires hardware to be connected")
    print()

def check_sudo():
    """Check if running with sudo"""
    return os.geteuid() == 0

def run_test(test_info):
    """Run a single test script"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    test_file = os.path.join(test_dir, test_info['file'])
    
    if not os.path.exists(test_file):
        print(f"[SKIP] Test file not found: {test_info['file']}")
        return None
    
    # Check sudo requirement
    if test_info['requires_sudo'] and not check_sudo():
        print(f"[SKIP] This test requires sudo. Run with: sudo python3 run_all_tests.py")
        return None
    
    # Build command
    cmd = ['python3', test_file]
    
    try:
        print(f"[RUNNING] {test_info['file']}...")
        print()
        
        # Run test (non-interactive)
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(test_file),
            capture_output=False,  # Show output in real-time
            text=True,
            timeout=300  # 5 minute timeout per test
        )
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] Test exceeded 5 minute limit")
        return False
    except KeyboardInterrupt:
        print(f"\n[INTERRUPTED] Test cancelled by user")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to run test: {e}")
        return False

def main():
    """Main test runner"""
    print_header()
    
    # Check if we have sudo
    has_sudo = check_sudo()
    if has_sudo:
        print("[INFO] Running with sudo - hardware tests will run")
    else:
        print("[INFO] Not running with sudo - hardware tests will be skipped")
        print("       Run with 'sudo python3 run_all_tests.py' to run all tests")
    
    print()
    print(f"Total tests: {len(TESTS)}")
    print()
    
    # Ask for confirmation
    try:
        response = input("Run all tests? (y/n): ").strip().lower()
        if response != 'y':
            print("[CANCELLED] Test run cancelled")
            return
    except (KeyboardInterrupt, EOFError):
        print("\n[CANCELLED] Test run cancelled")
        return
    
    # Results tracking
    results = {
        'passed': [],
        'failed': [],
        'skipped': []
    }
    
    # Run each test
    total_tests = len(TESTS)
    for i, test_info in enumerate(TESTS, 1):
        print_test_header(test_info, i, total_tests)
        
        # Check if we can run this test
        if test_info['requires_sudo'] and not has_sudo:
            print(f"[SKIP] Skipping {test_info['name']} - requires sudo")
            results['skipped'].append(test_info)
            time.sleep(1)
            continue
        
        # Run the test
        test_result = run_test(test_info)
        
        if test_result is None:
            # Skipped or cancelled
            if test_info not in results['skipped']:
                results['skipped'].append(test_info)
        elif test_result:
            print(f"\n[✓ PASS] {test_info['name']}")
            results['passed'].append(test_info)
        else:
            print(f"\n[✗ FAIL] {test_info['name']}")
            results['failed'].append(test_info)
        
        # Small delay between tests
        time.sleep(2)
    
    # Print summary
    print()
    print("=" * 70)
    print(" " * 25 + "TEST SUMMARY")
    print("=" * 70)
    print()
    
    print(f"Total Tests:  {total_tests}")
    print(f"Passed:       {len(results['passed'])}")
    print(f"Failed:       {len(results['failed'])}")
    print(f"Skipped:      {len(results['skipped'])}")
    print()
    
    if results['passed']:
        print("✓ PASSED TESTS:")
        for test in results['passed']:
            print(f"  - {test['name']}")
        print()
    
    if results['failed']:
        print("✗ FAILED TESTS:")
        for test in results['failed']:
            print(f"  - {test['name']}")
        print()
    
    if results['skipped']:
        print("⊘ SKIPPED TESTS:")
        for test in results['skipped']:
            reason = "requires sudo" if test['requires_sudo'] else "not available"
            print(f"  - {test['name']} ({reason})")
        print()
    
    print("=" * 70)
    
    # Final status
    if len(results['failed']) == 0 and len(results['skipped']) == 0:
        print("\n[SUCCESS] All tests passed! ✓")
        print("\nYour Raspberry Pi is ready for deployment!")
        return 0
    elif len(results['failed']) == 0:
        print("\n[PARTIAL] All runnable tests passed!")
        if results['skipped']:
            print("\nSome tests were skipped. Run with sudo to test hardware.")
        return 0
    else:
        print("\n[FAILED] Some tests failed. Review errors above.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Test run cancelled by user")
        sys.exit(130)

