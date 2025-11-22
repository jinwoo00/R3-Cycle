#!/usr/bin/env python3
"""
SQLite Database Setup for R3-Cycle Offline Mode
Creates local database for caching user data and queuing offline transactions

Usage: python3 setup_db.py

Author: R3-Cycle Team
Last Updated: 2025-11-21
"""

import sqlite3
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config

def create_database():
    """
    Create SQLite database with all required tables
    """
    print("=" * 60)
    print("R3-Cycle SQLite Database Setup")
    print("=" * 60)
    print()

    db_path = config.SQLITE_DB_PATH
    print(f"Database path: {db_path}")
    print()

    # Create directory if it doesn't exist
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"Created directory: {db_dir}")

    # Connect to database (creates file if doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("[1/5] Creating users_cache table...")

    # User cache table - stores local copy of user data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users_cache (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            rfid_tag TEXT UNIQUE,
            current_points INTEGER DEFAULT 0,
            total_paper_recycled INTEGER DEFAULT 0,
            total_transactions INTEGER DEFAULT 0,
            bonds_earned INTEGER DEFAULT 0,
            last_synced INTEGER,
            created_at INTEGER,
            updated_at INTEGER
        )
    ''')

    # Index for RFID lookup (most common query)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_rfid_tag
        ON users_cache(rfid_tag)
    ''')

    print("   ✓ users_cache table created")

    print("[2/5] Creating pending_transactions table...")

    # Pending transactions table - queues offline transactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            rfid_tag TEXT NOT NULL,
            weight REAL NOT NULL,
            metal_detected INTEGER NOT NULL,
            points_awarded INTEGER DEFAULT 0,
            status TEXT DEFAULT 'completed',
            rejection_reason TEXT,
            timestamp INTEGER NOT NULL,
            synced INTEGER DEFAULT 0,
            sync_attempts INTEGER DEFAULT 0,
            last_sync_attempt INTEGER,
            created_at INTEGER NOT NULL
        )
    ''')

    # Index for sync queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_synced
        ON pending_transactions(synced, sync_attempts)
    ''')

    print("   ✓ pending_transactions table created")

    print("[3/5] Creating pending_redemptions table...")

    # Pending redemptions table - queues offline redemptions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            reward_type TEXT NOT NULL,
            points_cost INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            synced INTEGER DEFAULT 0,
            sync_attempts INTEGER DEFAULT 0,
            last_sync_attempt INTEGER,
            created_at INTEGER NOT NULL
        )
    ''')

    # Index for sync queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_redemptions_synced
        ON pending_redemptions(synced, sync_attempts)
    ''')

    print("   ✓ pending_redemptions table created")

    print("[4/5] Creating sync_log table...")

    # Sync log table - tracks synchronization history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type TEXT NOT NULL,
            status TEXT NOT NULL,
            items_synced INTEGER DEFAULT 0,
            items_failed INTEGER DEFAULT 0,
            error_message TEXT,
            timestamp INTEGER NOT NULL
        )
    ''')

    print("   ✓ sync_log table created")

    print("[5/5] Creating metadata table...")

    # Metadata table - stores database version and settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at INTEGER
        )
    ''')

    # Insert database version
    cursor.execute('''
        INSERT OR REPLACE INTO metadata (key, value, updated_at)
        VALUES ('db_version', '1.0', ?)
    ''', (int(__import__('time').time()),))

    # Insert last sync timestamp
    cursor.execute('''
        INSERT OR IGNORE INTO metadata (key, value, updated_at)
        VALUES ('last_sync', '0', 0)
    ''', )

    print("   ✓ metadata table created")

    # Commit changes
    conn.commit()

    print()
    print("=" * 60)
    print("Database Setup Complete!")
    print("=" * 60)
    print()

    # Display database info
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    print(f"Tables created: {len(tables)}")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  - {table[0]}: {count} rows")

    print()
    print(f"Database file: {db_path}")
    print(f"Database size: {os.path.getsize(db_path)} bytes")
    print()

    # Close connection
    conn.close()

    return True

def verify_database():
    """
    Verify database structure is correct
    """
    print("Verifying database structure...")

    conn = sqlite3.connect(config.SQLITE_DB_PATH)
    cursor = conn.cursor()

    required_tables = [
        'users_cache',
        'pending_transactions',
        'pending_redemptions',
        'sync_log',
        'metadata'
    ]

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]

    missing_tables = []
    for table in required_tables:
        if table not in existing_tables:
            missing_tables.append(table)

    if missing_tables:
        print(f"❌ Missing tables: {', '.join(missing_tables)}")
        conn.close()
        return False

    print("✓ All required tables exist")

    # Verify indexes
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND sql IS NOT NULL
    """)
    indexes = cursor.fetchall()
    print(f"✓ {len(indexes)} indexes created")

    # Verify metadata
    cursor.execute("SELECT value FROM metadata WHERE key='db_version'")
    version = cursor.fetchone()
    if version:
        print(f"✓ Database version: {version[0]}")

    conn.close()
    print()
    print("Database verification passed!")

    return True

def reset_database():
    """
    WARNING: Drops all tables and recreates database
    Use only for testing or fresh install
    """
    print()
    print("⚠️  WARNING: This will delete ALL offline data!")
    print()
    response = input("Are you sure you want to reset the database? (yes/no): ")

    if response.lower() != 'yes':
        print("Reset cancelled")
        return False

    print()
    print("Resetting database...")

    db_path = config.SQLITE_DB_PATH

    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✓ Deleted existing database: {db_path}")

    # Recreate database
    create_database()

    print()
    print("Database reset complete!")

    return True

def main():
    """
    Main entry point
    """
    if len(sys.argv) > 1:
        if sys.argv[1] == '--reset':
            return reset_database()
        elif sys.argv[1] == '--verify':
            return verify_database()
        elif sys.argv[1] == '--help':
            print("R3-Cycle SQLite Database Setup")
            print()
            print("Usage:")
            print("  python3 setup_db.py           Create database")
            print("  python3 setup_db.py --reset   Reset database (deletes all data)")
            print("  python3 setup_db.py --verify  Verify database structure")
            print("  python3 setup_db.py --help    Show this help")
            return True
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
            return False

    # Default: create database
    success = create_database()

    if success:
        verify_database()

    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
