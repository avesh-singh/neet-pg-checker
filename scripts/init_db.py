#!/usr/bin/env python3
"""Initialize database tables for NEET PG application on Render.com"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys

def get_db_connection():
    """Create PostgreSQL database connection"""
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    try:
        if DATABASE_URL:
            # Production: Use DATABASE_URL from environment (Render.com provides this)
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            print("Using production database (DATABASE_URL)")
        else:
            # Local development: Use local PostgreSQL
            conn = psycopg2.connect(
                host='localhost',
                database='neetpg',
                user='avesh',
                cursor_factory=RealDictCursor
            )
            print("Using local PostgreSQL database")
        
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Make sure PostgreSQL is running and the database exists")
        sys.exit(1)

def create_tables():
    """Create necessary database tables in PostgreSQL"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("Creating database tables...")
    
    try:
        # Main counselling data table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS counselling_data (
            id SERIAL PRIMARY KEY,
            year INTEGER,
            round INTEGER,
            rank INTEGER,
            quota TEXT,
            state TEXT,
            college_name TEXT,
            course TEXT,
            category TEXT,
            sub_category TEXT,
            gender TEXT,
            physically_handicapped TEXT,
            marks_obtained INTEGER,
            max_marks INTEGER,
            status TEXT,
            date_of_admission TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        print("✅ Created counselling_data table")
        
        # Processed files tracking table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_files (
            id SERIAL PRIMARY KEY,
            filename TEXT UNIQUE,
            file_type TEXT,
            processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            records_count INTEGER
        )
        ''')
        print("✅ Created processed_files table")
        
        # Create indexes for better query performance
        indexes = [
            ('idx_rank', 'counselling_data(rank)'),
            ('idx_quota', 'counselling_data(quota)'),
            ('idx_category', 'counselling_data(category)'),
            ('idx_college_name', 'counselling_data(college_name)'),
            ('idx_course', 'counselling_data(course)'),
            ('idx_year_round', 'counselling_data(year, round)')
        ]
        
        for index_name, index_def in indexes:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}')
            print(f"✅ Created index {index_name}")
        
        # Insert some sample data if table is empty
        cursor.execute('SELECT COUNT(*) as count FROM counselling_data')
        count = cursor.fetchone()['count']
        
        if count == 0:
            print("Inserting sample data...")
            sample_data = [
                (2024, 3, 52, 'AI', 'Delhi', 'Vardhman Mahavir Medical College, New Delhi', 'MD - General Medicine', 'GENERAL'),
                (2024, 3, 73, 'AI', 'Tamil Nadu', 'Madras Medical College, Chennai', 'MD - General Medicine', 'OBC'),
                (2024, 3, 82, 'AI', 'Delhi', 'University College of Medical Sciences, Delhi', 'MD - General Medicine', 'GENERAL'),
                (2024, 3, 87, 'DU', 'Delhi', 'Maulana Azad Medical College, Delhi', 'MD - General Medicine', 'GENERAL'),
                (2024, 1, 3886, 'State Quota', 'Andhra Pradesh', 'Alluri Sitaram Raju Academy of Medical Sciences, Eluru', 'MD - Radio Diagnosis/Radiology', 'OBC'),
            ]
            
            for data in sample_data:
                cursor.execute('''
                INSERT INTO counselling_data 
                (year, round, rank, quota, state, college_name, course, category)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', data)
            
            print(f"✅ Inserted {len(sample_data)} sample records")
        
        conn.commit()
        print("✅ Database initialization completed successfully!")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

def verify_setup():
    """Verify database setup"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check tables exist
        cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        tables = [row['table_name'] for row in cursor.fetchall()]
        
        required_tables = ['counselling_data', 'processed_files']
        for table in required_tables:
            if table in tables:
                print(f"✅ Table {table} exists")
            else:
                print(f"❌ Table {table} missing")
                return False
        
        # Check data
        cursor.execute('SELECT COUNT(*) as count FROM counselling_data')
        count = cursor.fetchone()['count']
        print(f"✅ Total records in counselling_data: {count}")
        
        # Check indexes
        cursor.execute("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = 'counselling_data' AND schemaname = 'public'
        """)
        indexes = [row['indexname'] for row in cursor.fetchall()]
        print(f"✅ Indexes created: {len(indexes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying setup: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Initializing NEET PG database...")
    create_tables()
    
    print("\n🔍 Verifying setup...")
    if verify_setup():
        print("\n🎉 Database setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Deploy your application to Render.com")
        print("2. The database is ready to receive data")
        print("3. Use the API endpoints to check functionality")
    else:
        print("\n💥 Database setup failed!")
        sys.exit(1)
