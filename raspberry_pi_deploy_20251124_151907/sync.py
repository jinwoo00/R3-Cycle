#!/usr/bin/env python3
"""
R3-Cycle Sync Manager
Handles synchronization between local SQLite and backend API

Author: R3-Cycle Team
Last Updated: 2025-11-21
"""

import time
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import config
from database import DatabaseManager

class SyncManager:
    """Manages synchronization between local database and backend API"""

    def __init__(self, db_manager: DatabaseManager, api_client):
        """
        Initialize sync manager

        Args:
            db_manager: DatabaseManager instance
            api_client: APIClient instance from main.py
        """
        self.db = db_manager
        self.api = api_client
        self.is_online = False
        self.last_network_check = 0

    # ============================================
    # NETWORK STATUS
    # ============================================

    def check_network_status(self, force: bool = False) -> bool:
        """
        Check if backend API is reachable

        Args:
            force: Force check even if recently checked

        Returns:
            True if online, False if offline
        """
        current_time = time.time()

        # Use cached status if recently checked (unless forced)
        if not force and (current_time - self.last_network_check) < config.NETWORK_CHECK_INTERVAL:
            return self.is_online

        self.last_network_check = current_time

        try:
            # Quick health check with short timeout
            response = requests.get(
                f"{config.API_BASE_URL}/health",
                timeout=config.NETWORK_CHECK_TIMEOUT
            )

            if response.status_code == 200:
                if not self.is_online:
                    print("[SYNC] Network restored - going ONLINE")
                self.is_online = True
                return True
            else:
                if self.is_online:
                    print(f"[SYNC] Network issue - going OFFLINE (HTTP {response.status_code})")
                self.is_online = False
                return False

        except requests.exceptions.RequestException as e:
            if self.is_online:
                print(f"[SYNC] Network unreachable - going OFFLINE ({e})")
            self.is_online = False
            return False

    def wait_for_network(self, timeout: int = 30) -> bool:
        """
        Wait for network to become available

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if network available, False if timeout
        """
        start_time = time.time()
        attempts = 0

        print(f"[SYNC] Waiting for network (timeout: {timeout}s)...")

        while (time.time() - start_time) < timeout:
            attempts += 1

            if self.check_network_status(force=True):
                print(f"[SYNC] Network available after {attempts} attempts")
                return True

            time.sleep(5)  # Wait 5 seconds between attempts

        print(f"[SYNC] Network timeout after {attempts} attempts")
        return False

    # ============================================
    # USER CACHE SYNC
    # ============================================

    def sync_user_cache(self, rfid_tag: str = None) -> Tuple[bool, int]:
        """
        Sync user cache from backend

        Args:
            rfid_tag: Sync specific user, or all if None

        Returns:
            Tuple of (success, number of users synced)
        """
        if not self.check_network_status():
            print("[SYNC] Cannot sync user cache - offline")
            return False, 0

        try:
            if rfid_tag:
                # Sync specific user
                print(f"[SYNC] Syncing user: {rfid_tag}")
                response = self.api.verify_rfid(rfid_tag)

                if response and response.get('valid'):
                    user_data = response.get('user', {})
                    user_data['rfid_tag'] = rfid_tag  # Add RFID tag

                    if self.db.cache_user(user_data):
                        self.db.log_sync('user_cache', True, 1)
                        return True, 1
                    else:
                        self.db.log_sync('user_cache', False, 0, "Failed to cache user")
                        return False, 0
                else:
                    print(f"[SYNC] User not found or invalid: {rfid_tag}")
                    self.db.log_sync('user_cache', False, 0, "User not found")
                    return False, 0

            else:
                # Sync all users would require backend endpoint
                # For now, users are cached on-demand when they scan
                print("[SYNC] Full user cache sync not implemented (use on-demand caching)")
                return True, 0

        except Exception as e:
            print(f"[SYNC ERROR] User cache sync failed: {e}")
            self.db.log_sync('user_cache', False, 0, str(e))
            return False, 0

    def refresh_user_cache(self, rfid_tag: str) -> Optional[Dict]:
        """
        Refresh cached user data from backend

        Args:
            rfid_tag: RFID tag to refresh

        Returns:
            Updated user data if successful, None otherwise
        """
        success, count = self.sync_user_cache(rfid_tag)

        if success and count > 0:
            return self.db.get_user_by_rfid(rfid_tag)

        return None

    # ============================================
    # TRANSACTION SYNC
    # ============================================

    def sync_pending_transactions(self, limit: int = None) -> Tuple[bool, int, int]:
        """
        Sync pending transactions to backend

        Args:
            limit: Maximum number of transactions to sync

        Returns:
            Tuple of (all_success, synced_count, failed_count)
        """
        if not self.check_network_status():
            print("[SYNC] Cannot sync transactions - offline")
            return False, 0, 0

        pending = self.db.get_pending_transactions(limit)

        if not pending:
            print("[SYNC] No pending transactions to sync")
            return True, 0, 0

        print(f"[SYNC] Syncing {len(pending)} pending transactions...")

        synced_count = 0
        failed_count = 0

        for transaction in pending:
            try:
                # Submit transaction to backend
                result = self.api.submit_transaction(
                    rfid_tag=transaction['rfid_tag'],
                    weight=transaction['weight'],
                    metal_detected=transaction['metal_detected']
                )

                if result and result.get('accepted'):
                    # Mark as synced
                    backend_id = result.get('transactionId')
                    self.db.mark_transaction_synced(transaction['id'], backend_id)
                    synced_count += 1
                    print(f"  ✓ Transaction {transaction['id']} synced (backend ID: {backend_id})")

                else:
                    # Mark as failed
                    reason = result.get('reason', 'Unknown error') if result else 'No response'
                    self.db.mark_transaction_failed(transaction['id'], reason)
                    failed_count += 1
                    print(f"  ✗ Transaction {transaction['id']} failed: {reason}")

                # Small delay to avoid overwhelming backend
                time.sleep(0.5)

            except Exception as e:
                print(f"  ✗ Transaction {transaction['id']} error: {e}")
                self.db.mark_transaction_failed(transaction['id'], str(e))
                failed_count += 1

        # Log sync attempt
        all_success = (failed_count == 0)
        self.db.log_sync('transactions', all_success, synced_count,
                        f"{failed_count} failed" if failed_count > 0 else None)

        print(f"[SYNC] Transaction sync complete: {synced_count} synced, {failed_count} failed")
        return all_success, synced_count, failed_count

    def sync_single_transaction(self, transaction_id: int) -> bool:
        """
        Sync specific transaction

        Args:
            transaction_id: Local transaction ID

        Returns:
            True if synced successfully
        """
        if not self.check_network_status():
            print("[SYNC] Cannot sync transaction - offline")
            return False

        # Get transaction from database
        pending = self.db.get_pending_transactions()
        transaction = next((t for t in pending if t['id'] == transaction_id), None)

        if not transaction:
            print(f"[SYNC] Transaction {transaction_id} not found or already synced")
            return False

        try:
            result = self.api.submit_transaction(
                rfid_tag=transaction['rfid_tag'],
                weight=transaction['weight'],
                metal_detected=transaction['metal_detected']
            )

            if result and result.get('accepted'):
                backend_id = result.get('transactionId')
                self.db.mark_transaction_synced(transaction_id, backend_id)
                print(f"[SYNC] Transaction {transaction_id} synced successfully")
                return True
            else:
                reason = result.get('reason', 'Unknown error') if result else 'No response'
                self.db.mark_transaction_failed(transaction_id, reason)
                print(f"[SYNC] Transaction {transaction_id} sync failed: {reason}")
                return False

        except Exception as e:
            print(f"[SYNC ERROR] Transaction {transaction_id} sync error: {e}")
            self.db.mark_transaction_failed(transaction_id, str(e))
            return False

    # ============================================
    # REDEMPTION SYNC
    # ============================================

    def fetch_pending_redemptions(self) -> List[Dict]:
        """
        Fetch pending redemptions from backend

        Returns:
            List of pending redemption dicts
        """
        if not self.check_network_status():
            print("[SYNC] Cannot fetch redemptions - offline")
            return []

        try:
            # This would call the redemption/pending endpoint
            # For now, return empty list (backend integration needed)
            print("[SYNC] Fetching pending redemptions from backend...")

            headers = {
                "Content-Type": "application/json",
                "X-Machine-ID": config.MACHINE_ID,
                "X-Machine-Secret": config.MACHINE_SECRET
            }

            response = requests.get(
                f"{config.API_BASE_URL}/redemption/pending",
                headers=headers,
                timeout=config.API_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                redemptions = data.get('redemptions', [])

                # Queue redemptions locally
                queued_count = 0
                for redemption in redemptions:
                    redemption_id = self.db.queue_redemption(redemption)
                    if redemption_id:
                        queued_count += 1

                print(f"[SYNC] Queued {queued_count} pending redemptions")
                return redemptions

            else:
                print(f"[SYNC] Failed to fetch redemptions: HTTP {response.status_code}")
                return []

        except Exception as e:
            print(f"[SYNC ERROR] Failed to fetch redemptions: {e}")
            return []

    def report_dispensed_redemption(self, redemption_id: int, backend_id: str = None) -> bool:
        """
        Report to backend that redemption was dispensed

        Args:
            redemption_id: Local redemption ID
            backend_id: Backend redemption ID (if known)

        Returns:
            True if reported successfully
        """
        if not self.check_network_status():
            print("[SYNC] Cannot report redemption - offline (will retry later)")
            return False

        try:
            # This would call backend API to confirm dispensing
            # For now, just mark as dispensed locally
            return self.db.mark_redemption_dispensed(redemption_id)

        except Exception as e:
            print(f"[SYNC ERROR] Failed to report redemption: {e}")
            return False

    # ============================================
    # FULL SYNC
    # ============================================

    def full_sync(self) -> Dict:
        """
        Perform full synchronization (users + transactions + redemptions)

        Returns:
            Dict with sync results
        """
        print("[SYNC] Starting full sync...")

        results = {
            'online': False,
            'user_cache': {'success': False, 'count': 0},
            'transactions': {'success': False, 'synced': 0, 'failed': 0},
            'redemptions': {'success': False, 'count': 0},
            'timestamp': datetime.now().isoformat()
        }

        # Check network
        if not self.check_network_status(force=True):
            print("[SYNC] Full sync aborted - offline")
            return results

        results['online'] = True

        # Sync pending transactions
        print("[SYNC] Syncing pending transactions...")
        tx_success, tx_synced, tx_failed = self.sync_pending_transactions()
        results['transactions'] = {
            'success': tx_success,
            'synced': tx_synced,
            'failed': tx_failed
        }

        # Fetch pending redemptions
        print("[SYNC] Fetching pending redemptions...")
        redemptions = self.fetch_pending_redemptions()
        results['redemptions'] = {
            'success': True,
            'count': len(redemptions)
        }

        # User cache is synced on-demand, not in bulk
        results['user_cache'] = {
            'success': True,
            'count': 0,
            'note': 'Users cached on-demand when they scan RFID'
        }

        print(f"[SYNC] Full sync complete:")
        print(f"  Transactions: {tx_synced} synced, {tx_failed} failed")
        print(f"  Redemptions: {len(redemptions)} fetched")

        return results

    def auto_sync_loop(self, interval: int = None):
        """
        Continuous sync loop (runs in background thread)

        Args:
            interval: Sync interval in seconds (defaults to config.SYNC_INTERVAL)
        """
        interval = interval or config.SYNC_INTERVAL
        print(f"[SYNC] Starting auto-sync loop (interval: {interval}s)")

        while True:
            try:
                # Wait for interval
                time.sleep(interval)

                # Only sync if online
                if self.check_network_status():
                    print(f"[SYNC] Auto-sync triggered ({datetime.now().strftime('%H:%M:%S')})")
                    self.full_sync()
                else:
                    # Check if we have pending transactions
                    pending_count = self.db.get_pending_transactions_count()
                    if pending_count > 0:
                        print(f"[SYNC] Offline - {pending_count} transactions queued")

            except Exception as e:
                print(f"[SYNC ERROR] Auto-sync error: {e}")

    # ============================================
    # SMART SYNC (ONLINE/OFFLINE HANDLING)
    # ============================================

    def smart_verify_user(self, rfid_tag: str) -> Tuple[bool, Optional[Dict]]:
        """
        Verify user - tries backend first, falls back to cache

        Args:
            rfid_tag: RFID tag to verify

        Returns:
            Tuple of (valid, user_data)
        """
        # Try backend first if online
        if self.check_network_status():
            try:
                print(f"[SYNC] Verifying user online: {rfid_tag}")
                result = self.api.verify_rfid(rfid_tag)

                if result and result.get('valid'):
                    user_data = result.get('user', {})
                    user_data['rfid_tag'] = rfid_tag

                    # Cache user for offline mode
                    self.db.cache_user(user_data)

                    print(f"[SYNC] User verified online: {user_data.get('name')}")
                    return True, user_data

                else:
                    print(f"[SYNC] User not found on backend: {rfid_tag}")
                    return False, None

            except Exception as e:
                print(f"[SYNC WARNING] Backend verification failed, trying cache: {e}")
                # Fall through to cache lookup

        # Fallback to cache (offline mode)
        print(f"[SYNC] Checking user cache (offline mode): {rfid_tag}")
        cached_user = self.db.get_user_by_rfid(rfid_tag)

        if cached_user:
            if not cached_user.get('is_active', True):
                print(f"[SYNC] Cached user is inactive: {rfid_tag}")
                return False, None

            print(f"[SYNC] User verified from cache: {cached_user.get('name')}")
            return True, cached_user

        else:
            print(f"[SYNC] User not found in cache: {rfid_tag}")
            return False, None

    def smart_submit_transaction(self, rfid_tag: str, weight: float,
                                 metal_detected: bool) -> Tuple[bool, Dict]:
        """
        Submit transaction - tries backend first, queues if offline

        Args:
            rfid_tag: User's RFID tag
            weight: Paper weight in grams
            metal_detected: Whether metal was detected

        Returns:
            Tuple of (accepted, result_data)
        """
        # Calculate points
        points_earned = int(weight * 10)  # 10 points per gram

        transaction_data = {
            'rfid_tag': rfid_tag,
            'weight': weight,
            'metal_detected': metal_detected,
            'points_earned': points_earned,
            'timestamp': datetime.now().isoformat()
        }

        # Try backend first if online
        if self.check_network_status():
            try:
                print(f"[SYNC] Submitting transaction online: {weight}g")
                result = self.api.submit_transaction(rfid_tag, weight, metal_detected)

                if result and result.get('accepted'):
                    print(f"[SYNC] Transaction accepted online")

                    # Update user cache
                    cached_user = self.db.get_user_by_rfid(rfid_tag)
                    if cached_user:
                        self.db.update_user_points(rfid_tag, points_earned)

                    return True, result

                else:
                    reason = result.get('reason', 'Unknown') if result else 'No response'
                    print(f"[SYNC] Transaction rejected: {reason}")
                    return False, {'reason': reason}

            except Exception as e:
                print(f"[SYNC WARNING] Backend submission failed, queueing offline: {e}")
                # Fall through to offline queueing

        # Queue for offline sync
        print(f"[SYNC] Queueing transaction offline: {weight}g")
        transaction_id = self.db.queue_transaction(transaction_data)

        if transaction_id:
            # Update user points locally
            self.db.update_user_points(rfid_tag, points_earned)

            print(f"[SYNC] Transaction queued (ID: {transaction_id})")
            return True, {
                'accepted': True,
                'offline': True,
                'transaction_id': transaction_id,
                'points_earned': points_earned
            }

        else:
            print(f"[SYNC ERROR] Failed to queue transaction")
            return False, {'reason': 'Database error'}

# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

def create_sync_manager(db_manager: DatabaseManager, api_client) -> SyncManager:
    """
    Create sync manager instance

    Args:
        db_manager: DatabaseManager instance
        api_client: APIClient instance

    Returns:
        SyncManager instance
    """
    return SyncManager(db_manager, api_client)

if __name__ == "__main__":
    # Test sync operations
    print("=" * 60)
    print("R3-Cycle Sync Manager Test")
    print("=" * 60)
    print()

    from database import get_db

    db = get_db()

    # Mock API client for testing
    class MockAPIClient:
        def verify_rfid(self, rfid_tag):
            return {'valid': True, 'user': {'user_id': '123', 'name': 'Test User', 'current_points': 100}}

        def submit_transaction(self, rfid_tag, weight, metal_detected):
            return {'accepted': True, 'transactionId': 'TX123', 'points_earned': int(weight * 10)}

    api = MockAPIClient()
    sync = SyncManager(db, api)

    # Test network check
    print("[TEST] Checking network status...")
    is_online = sync.check_network_status(force=True)
    print(f"  Status: {'ONLINE' if is_online else 'OFFLINE'}")

    # Test smart user verification
    print("\n[TEST] Smart user verification...")
    valid, user_data = sync.smart_verify_user('TEST12345')
    if valid:
        print(f"  User: {user_data.get('name')} ({user_data.get('current_points')} points)")

    # Test smart transaction submission
    print("\n[TEST] Smart transaction submission...")
    accepted, result = sync.smart_submit_transaction('TEST12345', 15.5, False)
    if accepted:
        print(f"  Transaction accepted: {result.get('points_earned')} points")
        print(f"  Offline mode: {result.get('offline', False)}")

    # Test database stats
    print("\n[TEST] Database statistics:")
    stats = db.get_database_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    db.close()
    print("\n[TEST] Sync manager test complete!")
