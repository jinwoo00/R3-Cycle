#!/usr/bin/env python3
"""
R3-Cycle Database Manager
Handles all SQLite operations for offline mode

Author: R3-Cycle Team
Last Updated: 2025-11-21
"""

import sqlite3
import json
import time
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import config

class DatabaseManager:
    """Manages local SQLite database for offline mode"""

    def __init__(self, db_path: str = None):
        """
        Initialize database manager

        Args:
            db_path: Path to SQLite database (defaults to config.SQLITE_DB_PATH)
        """
        self.db_path = db_path or config.SQLITE_DB_PATH
        self.conn = None
        self.cursor = None
        self._connect()

    def _connect(self):
        """Establish connection to database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Access columns by name
            self.cursor = self.conn.cursor()
            print(f"[DB] Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to connect: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            print("[DB] Database connection closed")

    # ============================================
    # USER CACHE OPERATIONS
    # ============================================

    def cache_user(self, user_data: Dict) -> bool:
        """
        Cache user data locally for offline verification

        Args:
            user_data: Dict with keys: user_id, name, email, rfid_tag,
                      current_points, total_weight, is_active

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO users_cache (
                    user_id, name, email, rfid_tag, current_points,
                    total_weight, is_active, last_synced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data.get('user_id'),
                user_data.get('name'),
                user_data.get('email'),
                user_data.get('rfid_tag'),
                user_data.get('current_points', 0),
                user_data.get('total_weight', 0.0),
                user_data.get('is_active', True),
                int(time.time())  # Current timestamp
            ))

            self.conn.commit()
            print(f"[DB] Cached user: {user_data.get('name')} ({user_data.get('rfid_tag')})")
            return True

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to cache user: {e}")
            return False

    def get_user_by_rfid(self, rfid_tag: str) -> Optional[Dict]:
        """
        Retrieve cached user by RFID tag

        Args:
            rfid_tag: RFID tag to lookup

        Returns:
            Dict with user data if found, None otherwise
        """
        try:
            self.cursor.execute('''
                SELECT * FROM users_cache WHERE rfid_tag = ?
            ''', (rfid_tag,))

            row = self.cursor.fetchone()

            if row:
                # Check if cache is expired
                cache_age = int(time.time()) - row['last_synced']
                if cache_age > config.USER_CACHE_EXPIRY:
                    print(f"[DB WARNING] User cache expired ({cache_age}s old)")
                    # Don't delete, just warn - still usable for offline mode

                return {
                    'user_id': row['user_id'],
                    'name': row['name'],
                    'email': row['email'],
                    'rfid_tag': row['rfid_tag'],
                    'current_points': row['current_points'],
                    'total_weight': row['total_weight'],
                    'is_active': bool(row['is_active']),
                    'last_synced': row['last_synced']
                }

            return None

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to get user: {e}")
            return None

    def update_user_points(self, rfid_tag: str, points_to_add: int) -> bool:
        """
        Update user's points in local cache (offline mode)

        Args:
            rfid_tag: User's RFID tag
            points_to_add: Points to add

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cursor.execute('''
                UPDATE users_cache
                SET current_points = current_points + ?
                WHERE rfid_tag = ?
            ''', (points_to_add, rfid_tag))

            self.conn.commit()

            if self.cursor.rowcount > 0:
                print(f"[DB] Updated user points: +{points_to_add} for {rfid_tag}")
                return True
            else:
                print(f"[DB WARNING] User not found: {rfid_tag}")
                return False

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to update points: {e}")
            return False

    def get_cached_users_count(self) -> int:
        """Get number of cached users"""
        try:
            self.cursor.execute('SELECT COUNT(*) FROM users_cache')
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to count users: {e}")
            return 0

    # ============================================
    # TRANSACTION QUEUE OPERATIONS
    # ============================================

    def queue_transaction(self, transaction_data: Dict) -> Optional[int]:
        """
        Queue transaction for later sync (offline mode)

        Args:
            transaction_data: Dict with keys: rfid_tag, weight, metal_detected,
                            points_earned, timestamp

        Returns:
            Transaction ID if successful, None otherwise
        """
        try:
            self.cursor.execute('''
                INSERT INTO pending_transactions (
                    rfid_tag, weight, metal_detected, points_earned,
                    timestamp, sync_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction_data.get('rfid_tag'),
                transaction_data.get('weight'),
                transaction_data.get('metal_detected', False),
                transaction_data.get('points_earned', 0),
                transaction_data.get('timestamp'),
                'pending',  # Initial status
                int(time.time())
            ))

            self.conn.commit()
            transaction_id = self.cursor.lastrowid

            print(f"[DB] Queued transaction ID {transaction_id} for {transaction_data.get('rfid_tag')}")
            return transaction_id

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to queue transaction: {e}")
            return None

    def get_pending_transactions(self, limit: int = None) -> List[Dict]:
        """
        Get all pending transactions waiting to sync

        Args:
            limit: Maximum number of transactions to return

        Returns:
            List of transaction dicts
        """
        try:
            query = '''
                SELECT * FROM pending_transactions
                WHERE sync_status = 'pending'
                ORDER BY created_at ASC
            '''

            if limit:
                query += f' LIMIT {limit}'

            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            transactions = []
            for row in rows:
                transactions.append({
                    'id': row['id'],
                    'rfid_tag': row['rfid_tag'],
                    'weight': row['weight'],
                    'metal_detected': bool(row['metal_detected']),
                    'points_earned': row['points_earned'],
                    'timestamp': row['timestamp'],
                    'sync_status': row['sync_status'],
                    'retry_count': row['retry_count'],
                    'created_at': row['created_at']
                })

            return transactions

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to get pending transactions: {e}")
            return []

    def mark_transaction_synced(self, transaction_id: int, backend_id: str = None) -> bool:
        """
        Mark transaction as successfully synced

        Args:
            transaction_id: Local transaction ID
            backend_id: Backend transaction ID (if available)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cursor.execute('''
                UPDATE pending_transactions
                SET sync_status = 'synced',
                    synced_at = ?,
                    backend_transaction_id = ?
                WHERE id = ?
            ''', (int(time.time()), backend_id, transaction_id))

            self.conn.commit()
            print(f"[DB] Transaction {transaction_id} marked as synced")
            return True

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to mark transaction synced: {e}")
            return False

    def mark_transaction_failed(self, transaction_id: int, error_message: str = None) -> bool:
        """
        Mark transaction as failed to sync (will retry later)

        Args:
            transaction_id: Local transaction ID
            error_message: Error message to store

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cursor.execute('''
                UPDATE pending_transactions
                SET retry_count = retry_count + 1,
                    last_error = ?
                WHERE id = ?
            ''', (error_message, transaction_id))

            self.conn.commit()

            # Check if max retries reached
            self.cursor.execute('SELECT retry_count FROM pending_transactions WHERE id = ?', (transaction_id,))
            row = self.cursor.fetchone()

            if row and row['retry_count'] >= config.MAX_SYNC_RETRIES:
                print(f"[DB WARNING] Transaction {transaction_id} exceeded max retries, marking as failed")
                self.cursor.execute('''
                    UPDATE pending_transactions
                    SET sync_status = 'failed'
                    WHERE id = ?
                ''', (transaction_id,))
                self.conn.commit()

            return True

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to mark transaction failed: {e}")
            return False

    def get_pending_transactions_count(self) -> int:
        """Get count of pending transactions"""
        try:
            self.cursor.execute('''
                SELECT COUNT(*) FROM pending_transactions
                WHERE sync_status = 'pending'
            ''')
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to count pending transactions: {e}")
            return 0

    def cleanup_old_transactions(self, days: int = 30) -> int:
        """
        Delete synced transactions older than specified days

        Args:
            days: Number of days to keep

        Returns:
            Number of deleted transactions
        """
        try:
            cutoff_timestamp = int(time.time()) - (days * 24 * 60 * 60)

            self.cursor.execute('''
                DELETE FROM pending_transactions
                WHERE sync_status = 'synced'
                AND synced_at < ?
            ''', (cutoff_timestamp,))

            self.conn.commit()
            deleted_count = self.cursor.rowcount

            if deleted_count > 0:
                print(f"[DB] Cleaned up {deleted_count} old synced transactions")

            return deleted_count

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to cleanup transactions: {e}")
            return 0

    # ============================================
    # REDEMPTION QUEUE OPERATIONS
    # ============================================

    def queue_redemption(self, redemption_data: Dict) -> Optional[int]:
        """
        Queue redemption for dispensing (offline mode)

        Args:
            redemption_data: Dict with keys: user_id, rfid_tag, reward_type,
                           points_cost, timestamp

        Returns:
            Redemption ID if successful, None otherwise
        """
        try:
            self.cursor.execute('''
                INSERT INTO pending_redemptions (
                    user_id, rfid_tag, reward_type, points_cost,
                    timestamp, dispensed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                redemption_data.get('user_id'),
                redemption_data.get('rfid_tag'),
                redemption_data.get('reward_type'),
                redemption_data.get('points_cost'),
                redemption_data.get('timestamp'),
                False,  # Not dispensed yet
                int(time.time())
            ))

            self.conn.commit()
            redemption_id = self.cursor.lastrowid

            print(f"[DB] Queued redemption ID {redemption_id} for {redemption_data.get('rfid_tag')}")
            return redemption_id

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to queue redemption: {e}")
            return None

    def get_pending_redemptions(self, rfid_tag: str = None) -> List[Dict]:
        """
        Get pending redemptions waiting to be dispensed

        Args:
            rfid_tag: Filter by specific user (optional)

        Returns:
            List of redemption dicts
        """
        try:
            if rfid_tag:
                self.cursor.execute('''
                    SELECT * FROM pending_redemptions
                    WHERE dispensed = 0 AND rfid_tag = ?
                    ORDER BY created_at ASC
                ''', (rfid_tag,))
            else:
                self.cursor.execute('''
                    SELECT * FROM pending_redemptions
                    WHERE dispensed = 0
                    ORDER BY created_at ASC
                ''')

            rows = self.cursor.fetchall()

            redemptions = []
            for row in rows:
                redemptions.append({
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'rfid_tag': row['rfid_tag'],
                    'reward_type': row['reward_type'],
                    'points_cost': row['points_cost'],
                    'timestamp': row['timestamp'],
                    'dispensed': bool(row['dispensed']),
                    'created_at': row['created_at']
                })

            return redemptions

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to get pending redemptions: {e}")
            return []

    def mark_redemption_dispensed(self, redemption_id: int) -> bool:
        """
        Mark redemption as dispensed

        Args:
            redemption_id: Redemption ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cursor.execute('''
                UPDATE pending_redemptions
                SET dispensed = 1,
                    dispensed_at = ?
                WHERE id = ?
            ''', (int(time.time()), redemption_id))

            self.conn.commit()
            print(f"[DB] Redemption {redemption_id} marked as dispensed")
            return True

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to mark redemption dispensed: {e}")
            return False

    # ============================================
    # SYNC LOG OPERATIONS
    # ============================================

    def log_sync(self, sync_type: str, success: bool,
                 records_synced: int = 0, error_message: str = None) -> bool:
        """
        Log sync attempt

        Args:
            sync_type: Type of sync (e.g., 'user_cache', 'transactions')
            success: Whether sync was successful
            records_synced: Number of records synced
            error_message: Error message if failed

        Returns:
            True if logged successfully
        """
        try:
            self.cursor.execute('''
                INSERT INTO sync_log (
                    sync_type, success, records_synced, error_message, timestamp
                ) VALUES (?, ?, ?, ?, ?)
            ''', (sync_type, success, records_synced, error_message, int(time.time())))

            self.conn.commit()
            return True

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to log sync: {e}")
            return False

    def get_last_sync(self, sync_type: str = None) -> Optional[Dict]:
        """
        Get last sync record

        Args:
            sync_type: Filter by sync type (optional)

        Returns:
            Dict with sync info if found, None otherwise
        """
        try:
            if sync_type:
                self.cursor.execute('''
                    SELECT * FROM sync_log
                    WHERE sync_type = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (sync_type,))
            else:
                self.cursor.execute('''
                    SELECT * FROM sync_log
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''')

            row = self.cursor.fetchone()

            if row:
                return {
                    'id': row['id'],
                    'sync_type': row['sync_type'],
                    'success': bool(row['success']),
                    'records_synced': row['records_synced'],
                    'error_message': row['error_message'],
                    'timestamp': row['timestamp']
                }

            return None

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to get last sync: {e}")
            return None

    # ============================================
    # METADATA OPERATIONS
    # ============================================

    def set_metadata(self, key: str, value: str) -> bool:
        """
        Set metadata value

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            True if successful
        """
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO metadata (key, value)
                VALUES (?, ?)
            ''', (key, value))

            self.conn.commit()
            return True

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to set metadata: {e}")
            return False

    def get_metadata(self, key: str, default: str = None) -> Optional[str]:
        """
        Get metadata value

        Args:
            key: Metadata key
            default: Default value if not found

        Returns:
            Metadata value or default
        """
        try:
            self.cursor.execute('SELECT value FROM metadata WHERE key = ?', (key,))
            row = self.cursor.fetchone()

            if row:
                return row['value']

            return default

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to get metadata: {e}")
            return default

    # ============================================
    # STATISTICS
    # ============================================

    def get_database_stats(self) -> Dict:
        """
        Get database statistics

        Returns:
            Dict with database statistics
        """
        try:
            stats = {
                'cached_users': 0,
                'pending_transactions': 0,
                'synced_transactions': 0,
                'failed_transactions': 0,
                'pending_redemptions': 0,
                'dispensed_redemptions': 0,
                'last_sync': None,
                'db_version': self.get_metadata('db_version', '1.0.0')
            }

            # Cached users
            self.cursor.execute('SELECT COUNT(*) FROM users_cache')
            stats['cached_users'] = self.cursor.fetchone()[0]

            # Pending transactions
            self.cursor.execute("SELECT COUNT(*) FROM pending_transactions WHERE sync_status = 'pending'")
            stats['pending_transactions'] = self.cursor.fetchone()[0]

            # Synced transactions
            self.cursor.execute("SELECT COUNT(*) FROM pending_transactions WHERE sync_status = 'synced'")
            stats['synced_transactions'] = self.cursor.fetchone()[0]

            # Failed transactions
            self.cursor.execute("SELECT COUNT(*) FROM pending_transactions WHERE sync_status = 'failed'")
            stats['failed_transactions'] = self.cursor.fetchone()[0]

            # Pending redemptions
            self.cursor.execute('SELECT COUNT(*) FROM pending_redemptions WHERE dispensed = 0')
            stats['pending_redemptions'] = self.cursor.fetchone()[0]

            # Dispensed redemptions
            self.cursor.execute('SELECT COUNT(*) FROM pending_redemptions WHERE dispensed = 1')
            stats['dispensed_redemptions'] = self.cursor.fetchone()[0]

            # Last sync
            last_sync = self.get_last_sync()
            if last_sync:
                stats['last_sync'] = datetime.fromtimestamp(last_sync['timestamp']).isoformat()

            return stats

        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to get stats: {e}")
            return {}

# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

def get_db() -> DatabaseManager:
    """
    Get database manager instance

    Returns:
        DatabaseManager instance
    """
    return DatabaseManager()

if __name__ == "__main__":
    # Test database operations
    print("=" * 60)
    print("R3-Cycle Database Manager Test")
    print("=" * 60)
    print()

    db = get_db()

    # Test user caching
    print("[TEST] Caching test user...")
    db.cache_user({
        'user_id': 'test_user_123',
        'name': 'Test User',
        'email': 'test@example.com',
        'rfid_tag': 'TEST12345',
        'current_points': 100,
        'total_weight': 50.5,
        'is_active': True
    })

    # Test user retrieval
    print("\n[TEST] Retrieving user by RFID...")
    user = db.get_user_by_rfid('TEST12345')
    if user:
        print(f"  Found: {user['name']} with {user['current_points']} points")

    # Test transaction queueing
    print("\n[TEST] Queueing test transaction...")
    transaction_id = db.queue_transaction({
        'rfid_tag': 'TEST12345',
        'weight': 15.5,
        'metal_detected': False,
        'points_earned': 10,
        'timestamp': datetime.now().isoformat()
    })
    print(f"  Transaction ID: {transaction_id}")

    # Test statistics
    print("\n[TEST] Database statistics:")
    stats = db.get_database_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    db.close()
    print("\n[TEST] Database test complete!")
