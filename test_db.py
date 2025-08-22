#!/usr/bin/env python3
"""Test script to verify database connection and basic functionality"""

import os
import sys

def test_sqlite():
    """Test SQLite connection"""
    print("=== Testing SQLite Connection ===")
    try:
        import sqlite3
        conn = sqlite3.connect('neet_pg_counselling.db')
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT COUNT(*) FROM counselling_data")
        count = cursor.fetchone()[0]
        print(f"✅ SQLite: Found {count} records in counselling_data")
        
        cursor.execute("SELECT COUNT(*) FROM processed_files")
        file_count = cursor.fetchone()[0]
        print(f"✅ SQLite: Found {file_count} processed files")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ SQLite Error: {e}")
        return False

def test_postgresql():
    """Test PostgreSQL connection"""
    print("\n=== Testing PostgreSQL Connection ===")
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("⚠️  DATABASE_URL not set, skipping PostgreSQL test")
        return True
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT COUNT(*) FROM counselling_data")
        count = cursor.fetchone()[0]
        print(f"✅ PostgreSQL: Found {count} records in counselling_data")
        
        cursor.execute("SELECT COUNT(*) FROM processed_files")
        file_count = cursor.fetchone()[0]
        print(f"✅ PostgreSQL: Found {file_count} processed files")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ PostgreSQL Error: {e}")
        return False

def test_flask_app():
    """Test Flask app database connection"""
    print("\n=== Testing Flask App Connection ===")
    try:
        # Import our Flask app
        from app import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if os.getenv('DATABASE_URL'):
            print("🔗 Using PostgreSQL connection")
        else:
            print("🔗 Using SQLite connection")
        
        cursor.execute("SELECT COUNT(*) FROM counselling_data")
        count = cursor.fetchone()[0]
        print(f"✅ Flask App: Found {count} records")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Flask App Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Database Connection Test\n")
    
    results = []
    results.append(test_sqlite())
    results.append(test_postgresql())
    results.append(test_flask_app())
    
    print(f"\n📊 Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)