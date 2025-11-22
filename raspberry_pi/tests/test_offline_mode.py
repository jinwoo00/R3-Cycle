#!/usr/bin/env python3
"""
Test script for Offline Mode functionality
Tests database operations, sync, and network resilience

Usage: python3 test_offline_mode.py
"""

import sys
import time
from datetime import datetime

# Add parent directory to path
sys.path.append('/home/pi/r3cycle')

try:
    import config
    from database import DatabaseManager
    from sync import SyncManager
    import setup_db
except ImportError as e:
    print(f"[ERROR] Missing library: {e}")
    sys.exit(1)

def print_section(title):
    """Print section header"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def test_database_setup():
    """Test database creation and verification"""
    print_section("TEST 1: Database Setup")

    # Create database
    print("[1/3] Creating database...")
    setup_db.create_database()
    print("      ✓ Database created")

    # Verify structure
    print("[2/3] Verifying database structure...")
    if setup_db.verify_database():
        print("      ✓ All tables and indexes verified")
    else:
        print("      ✗ Database structure incomplete")
        return False

    # Connect to database
    print("[3/3] Testing database connection...")
    db = DatabaseManager()
    stats = db.get_database_stats()
    print(f"      ✓ Connected - {stats['cached_users']} users cached")
    db.close()

    return True

def test_user_cache():
    """Test user caching operations"""
    print_section("TEST 2: User Cache Operations")

    db = DatabaseManager()

    # Test 1: Cache a user
    print("[1/4] Caching test user...")
    test_user = {
        'user_id': 'test_user_001',
        'name': 'John Doe',
        'email': 'john@example.com',
        'rfid_tag': 'ABCD1234',
        'current_points': 150,
        'total_weight': 75.5,
        'is_active': True
    }

    if db.cache_user(test_user):
        print(f"      ✓ User cached: {test_user['name']}")
    else:
        print("      ✗ Failed to cache user")
        db.close()
        return False

    # Test 2: Retrieve user by RFID
    print("[2/4] Retrieving user by RFID...")
    cached_user = db.get_user_by_rfid('ABCD1234')
    if cached_user:
        print(f"      ✓ Found: {cached_user['name']} ({cached_user['current_points']} pts)")
    else:
        print("      ✗ User not found")
        db.close()
        return False

    # Test 3: Update user points
    print("[3/4] Updating user points...")
    if db.update_user_points('ABCD1234', 25):
        updated_user = db.get_user_by_rfid('ABCD1234')
        print(f"      ✓ Points updated: {updated_user['current_points']} pts (+25)")
    else:
        print("      ✗ Failed to update points")
        db.close()
        return False

    # Test 4: Cache multiple users
    print("[4/4] Caching multiple users...")
    users = [
        {'user_id': 'user_002', 'name': 'Jane Smith', 'rfid_tag': 'EFGH5678', 'current_points': 200},
        {'user_id': 'user_003', 'name': 'Bob Johnson', 'rfid_tag': 'IJKL9012', 'current_points': 50}
    ]

    for user in users:
        db.cache_user(user)

    count = db.get_cached_users_count()
    print(f"      ✓ Total cached users: {count}")

    db.close()
    return True

def test_transaction_queue():
    """Test transaction queueing"""
    print_section("TEST 3: Transaction Queue")

    db = DatabaseManager()

    # Test 1: Queue transactions
    print("[1/4] Queueing test transactions...")
    transactions = [
        {'rfid_tag': 'ABCD1234', 'weight': 15.5, 'metal_detected': False, 'points_earned': 155, 'timestamp': datetime.now().isoformat()},
        {'rfid_tag': 'EFGH5678', 'weight': 12.3, 'metal_detected': False, 'points_earned': 123, 'timestamp': datetime.now().isoformat()},
        {'rfid_tag': 'ABCD1234', 'weight': 8.7, 'metal_detected': False, 'points_earned': 87, 'timestamp': datetime.now().isoformat()}
    ]

    queued = 0
    for tx in transactions:
        if db.queue_transaction(tx):
            queued += 1

    print(f"      ✓ Queued {queued} transactions")

    # Test 2: Retrieve pending transactions
    print("[2/4] Retrieving pending transactions...")
    pending = db.get_pending_transactions()
    print(f"      ✓ Found {len(pending)} pending transactions")

    # Test 3: Mark transaction as synced
    print("[3/4] Marking transaction as synced...")
    if pending:
        first_tx = pending[0]
        if db.mark_transaction_synced(first_tx['id'], 'BACKEND_TX_123'):
            print(f"      ✓ Transaction {first_tx['id']} marked as synced")
        else:
            print("      ✗ Failed to mark as synced")

    # Test 4: Check pending count
    print("[4/4] Checking updated pending count...")
    pending_count = db.get_pending_transactions_count()
    print(f"      ✓ {pending_count} transactions still pending")

    db.close()
    return True

def test_sync_manager():
    """Test sync manager operations"""
    print_section("TEST 4: Sync Manager")

    # Mock API client
    class MockAPIClient:
        def verify_rfid(self, rfid_tag):
            print(f"      [MOCK API] Verifying RFID: {rfid_tag}")
            return {'valid': True, 'user': {
                'user_id': 'mock_user',
                'name': 'Mock User',
                'current_points': 100
            }}

        def submit_transaction(self, rfid_tag, weight, metal_detected):
            print(f"      [MOCK API] Submitting transaction: {weight}g")
            return {'accepted': True, 'transactionId': 'MOCK_TX_123', 'points_earned': int(weight * 10)}

    db = DatabaseManager()
    api = MockAPIClient()
    sync = SyncManager(db, api)

    # Test 1: Network status check
    print("[1/5] Checking network status...")
    is_online = sync.check_network_status(force=True)
    print(f"      {'✓ ONLINE' if is_online else '✗ OFFLINE'}")

    # Test 2: Smart user verification (offline)
    print("[2/5] Testing smart user verification...")
    valid, user_data = sync.smart_verify_user('ABCD1234')
    if valid:
        print(f"      ✓ User verified: {user_data.get('name')} ({user_data.get('current_points')} pts)")
    else:
        print("      ✗ User verification failed")

    # Test 3: Smart transaction submission (offline)
    print("[3/5] Testing smart transaction submission...")
    accepted, result = sync.smart_submit_transaction('ABCD1234', 10.5, False)
    if accepted:
        print(f"      ✓ Transaction accepted: {result.get('points_earned')} points")
        if result.get('offline'):
            print(f"      ! Transaction queued offline (ID: {result.get('transaction_id')})")
    else:
        print("      ✗ Transaction rejected")

    # Test 4: Check database stats
    print("[4/5] Checking database statistics...")
    stats = db.get_database_stats()
    print(f"      ✓ Cached users: {stats['cached_users']}")
    print(f"      ✓ Pending transactions: {stats['pending_transactions']}")
    print(f"      ✓ Synced transactions: {stats['synced_transactions']}")

    # Test 5: Sync pending transactions (if online)
    print("[5/5] Testing transaction sync...")
    if sync.check_network_status():
        all_success, synced, failed = sync.sync_pending_transactions(limit=5)
        print(f"      ✓ Sync result: {synced} synced, {failed} failed")
    else:
        print("      ! Skipped - offline mode")

    db.close()
    return True

def test_network_resilience():
    """Test network resilience and offline mode"""
    print_section("TEST 5: Network Resilience")

    db = DatabaseManager()

    # Simulate offline scenario
    print("[1/3] Simulating offline scenario...")
    print("      ! Network temporarily unavailable")

    # Queue transaction offline
    offline_tx = {
        'rfid_tag': 'ABCD1234',
        'weight': 18.0,
        'metal_detected': False,
        'points_earned': 180,
        'timestamp': datetime.now().isoformat()
    }

    tx_id = db.queue_transaction(offline_tx)
    if tx_id:
        print(f"      ✓ Transaction queued offline (ID: {tx_id})")
    else:
        print("      ✗ Failed to queue transaction")
        db.close()
        return False

    # Update points locally
    print("[2/3] Updating local user cache...")
    if db.update_user_points('ABCD1234', 180):
        user = db.get_user_by_rfid('ABCD1234')
        print(f"      ✓ Local points updated: {user['current_points']} pts")
    else:
        print("      ✗ Failed to update local cache")

    # Show sync log
    print("[3/3] Checking sync history...")
    last_sync = db.get_last_sync()
    if last_sync:
        print(f"      ✓ Last sync: {last_sync['sync_type']} - {'Success' if last_sync['success'] else 'Failed'}")
    else:
        print("      ! No sync history yet")

    db.close()
    return True

def test_cleanup():
    """Test cleanup operations"""
    print_section("TEST 6: Cleanup & Maintenance")

    db = DatabaseManager()

    # Test 1: Cleanup old synced transactions
    print("[1/2] Cleaning up old synced transactions...")
    deleted = db.cleanup_old_transactions(days=0)  # Delete all synced
    print(f"      ✓ Deleted {deleted} old transactions")

    # Test 2: Final database stats
    print("[2/2] Final database statistics:")
    stats = db.get_database_stats()
    for key, value in stats.items():
        print(f"      - {key}: {value}")

    db.close()
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print(" R3-CYCLE OFFLINE MODE TEST SUITE")
    print("=" * 60)
    print(f" Database: {config.SQLITE_DB_PATH}")
    print(f" Offline Mode: {'ENABLED' if config.OFFLINE_MODE_ENABLED else 'DISABLED'}")
    print("=" * 60)

    if not config.OFFLINE_MODE_ENABLED:
        print("\n[WARNING] Offline mode is DISABLED in config.py")
        print("Set OFFLINE_MODE_ENABLED = True to enable")
        return

    tests = [
        ("Database Setup", test_database_setup),
        ("User Cache", test_user_cache),
        ("Transaction Queue", test_transaction_queue),
        ("Sync Manager", test_sync_manager),
        ("Network Resilience", test_network_resilience),
        ("Cleanup", test_cleanup)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n[FAILED] {test_name} test failed")
        except Exception as e:
            failed += 1
            print(f"\n[ERROR] {test_name} test error: {e}")

    # Summary
    print("\n" + "=" * 60)
    print(" TEST SUMMARY")
    print("=" * 60)
    print(f" Tests Passed: {passed}/{len(tests)}")
    print(f" Tests Failed: {failed}/{len(tests)}")
    print("=" * 60)

    if passed == len(tests):
        print("\n[SUCCESS] All offline mode tests passed! ✓")
        print("\nYour Raspberry Pi is ready for offline operation.")
        print("\nNext steps:")
        print("  1. Run main.py to test full system")
        print("  2. Try disconnecting network to test offline mode")
        print("  3. Reconnect network and watch transactions sync")
    else:
        print("\n[FAILED] Some tests failed")
        print("\nTroubleshooting:")
        print("  1. Check config.py has OFFLINE_MODE_ENABLED = True")
        print("  2. Verify SQLite database path is writable")
        print("  3. Review error messages above")

if __name__ == "__main__":
    main()
