#!/usr/bin/env python3
"""
Script to recreate database tables with the new schema
"""
import os
import sys
from pdf_uploader import NEETPGDataProcessor

if __name__ == "__main__":
    # Initialize processor
    processor = NEETPGDataProcessor()
    
    # Test database connection first
    if not processor.test_connection():
        print("❌ Cannot proceed without database connection!")
        processor.close()
        sys.exit(1)
    
    print("=== Recreating Database Tables ===")
    
    try:
        # Drop existing tables
        print("Dropping existing tables...")
        processor.cursor.execute('DROP TABLE IF EXISTS counselling_data CASCADE')
        processor.cursor.execute('DROP TABLE IF EXISTS processed_files CASCADE')
        processor.conn.commit()
        print("✅ Tables dropped successfully")
        
        # Recreate tables with new schema
        print("Creating tables with new schema...")
        processor.create_tables()
        print("✅ Tables created successfully")
        
        # Verify the new schema
        processor.cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'counselling_data' 
        ORDER BY ordinal_position
        """)
        
        columns = processor.cursor.fetchall()
        print(f"\n=== New Table Schema ({len(columns)} columns) ===")
        for col_name, data_type in columns:
            print(f"  {col_name}: {data_type}")
        
    except Exception as e:
        print(f"❌ Error recreating tables: {e}")
        processor.conn.rollback()
    
    # Close connection
    processor.close()
    print("\n=== Table Recreation Complete ===")