import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import PyPDF2
import pdfplumber
import re
from datetime import datetime
import json
import os
import glob

class NEETPGDataProcessor:
    def __init__(self, db_name='neet_pg_counselling.db'):
        """Initialize the processor with database connection"""
        # Use PostgreSQL connection from environment or local config
        self.db_config = self.get_db_config()
        self.conn = self.get_db_connection()
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def get_db_config(self):
        """Get database configuration from environment or use defaults"""
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'neetpg'),
            'user': os.getenv('DB_USER', 'avesh'),
            'password': os.getenv('DB_PASSWORD', ''),
            'port': os.getenv('DB_PORT', '5432')
        }
    
    def get_db_connection(self):
        """Create PostgreSQL database connection"""
        try:
            conn = psycopg2.connect(
                host=self.db_config['host'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                port=self.db_config['port']
            )
            return conn
        except Exception as e:
            print(f"Error connecting to PostgreSQL: {e}")
            raise
    
    def create_tables(self):
        """Create necessary database tables using PostgreSQL syntax"""
        
        # Main colleges data table
        self.cursor.execute('''
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
        
        # Create indexes for faster queries
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_rank ON counselling_data(rank)
        ''')
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_quota ON counselling_data(quota)
        ''')
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_category ON counselling_data(category)
        ''')
        
        # Table for storing processed files
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_files (
            id SERIAL PRIMARY KEY,
            filename TEXT UNIQUE,
            file_type TEXT,
            processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            records_count INTEGER
        )
        ''')
        
        self.conn.commit()
    
    def process_state_quota_pdf(self, pdf_path):
        """Process State Quota PDF page by page to prevent memory issues"""
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                print(f"    Processing page {page_num + 1}/{len(pdf.pages)}")
                
                # Extract tables if present
                tables = page.extract_tables()
                
                if tables:
                    for table in tables:
                        # Skip header row (index 0)
                        for row in table[1:]:
                            if row and len(row) >= 11:  # Ensure we have enough columns
                                record = self.parse_state_quota_row(row)
                                if record:
                                    yield record
    
    def parse_state_quota_row(self, row):
        """Parse a row from state quota table"""
        try:
            # Row structure: [State, College Name, Course, Name of Student, Gender, DOB, 
            # Admitted By, Sub Category, Physically Handicapped, Exam Name/Roll, Exam Rank, 
            # Marks, PG Teacher, Stipend, Student Regn, Council, Date of Admission]
            
            if not row or len(row) < 11:
                return None
            
            record = {}
            
            # Extract state (column 0)
            if row[0]:
                record['state'] = row[0].strip()
            
            # Extract college name (column 1) 
            if row[1]:
                record['college_name'] = row[1].strip()
            
            # Extract course (column 2)
            if row[2]:
                record['course'] = row[2].strip()
            
            # Extract gender (column 4)
            if row[4]:
                record['gender'] = row[4].strip()
            
            # Extract quota info (column 6) - "Admitted By"
            if row[6]:
                record['quota'] = row[6].strip()
            
            # Extract category (column 7) - "Sub Category"
            if row[7]:
                record['category'] = row[7].strip()
            
            # Extract rank from column 10 - "Exam Rank AIR/State Rank"
            if row[10]:
                rank_text = str(row[10]).strip()
                # Extract numeric rank - could be like "25579" or "94638"
                rank_match = re.search(r'(\d{4,6})', rank_text)
                if rank_match:
                    record['rank'] = int(rank_match.group(1))
            
            # Extract marks (column 11) - "Marks Obtained/Maximum Marks"
            if row[11]:
                marks_text = str(row[11]).strip()
                marks_match = re.search(r'(\d+)\s*/\s*(\d+)', marks_text)
                if marks_match:
                    record['marks_obtained'] = int(marks_match.group(1))
                    record['max_marks'] = int(marks_match.group(2))
            
            # Set defaults
            record['year'] = 2024
            record['round'] = 1  # State quota is typically round 1
            
            return record if 'rank' in record and record['rank'] else None
            
        except Exception as e:
            print(f"Error parsing state quota row: {e}")
            return None
    
    def process_all_india_pdf(self, pdf_path):
        """Process All India Quota PDF page by page to prevent memory issues"""
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                print(f"    Processing page {page_num + 1}/{len(pdf.pages)}")
                
                # Extract tables if present
                tables = page.extract_tables()
                
                if tables:
                    for table in tables:
                        # Skip header rows (first 2-3 rows typically)
                        for i, row in enumerate(table):
                            if i < 3:  # Skip header rows
                                continue
                            if row and len(row) >= 5:
                                record = self.parse_all_india_row(row)
                                if record:
                                    yield record
                else:
                    # Fallback to text extraction
                    text = page.extract_text()
                    records = self.parse_all_india_text(text)
                    for record in records:
                        yield record
    
    def parse_all_india_row(self, row):
        """Parse a row from All India quota table"""
        if not row or len(row) < 5:
            return None
        
        record = {}
        try:
            # pg_round_3.pdf structure has multiple rounds in same row
            # Row structure: [Rank, Round1_Quota, Round1_Institute, Round1_Course, Round1_Remarks, 
            #                Round2_Quota, Round2_Institute, Round2_Course, Round2_Remarks,
            #                Round3_Quota, ..., Round3_Institute, Round3_Course, Round3_Category, Round3_Remarks]
            
            # Extract rank (column 0)
            if row[0] and str(row[0]).isdigit():
                record['rank'] = int(row[0])
            
            # For Round 3 data (this PDF is specifically Round 3)
            # Look for Round 3 columns (around index 10-13)
            round3_quota_col = 9  # Approximate position
            round3_institute_col = 11
            round3_course_col = 12
            round3_category_col = 13
            
            # Try to find the actual Round 3 data
            for i in range(9, min(len(row), 15)):  # Search in Round 3 area
                if row[i] and isinstance(row[i], str):
                    # Check if this looks like a quota (AI, IP, etc.)
                    if row[i].strip() in ['AI', 'IP', 'DU', 'All India']:
                        record['quota'] = row[i].strip()
                        # Institute should be next non-empty column
                        for j in range(i+1, min(len(row), i+4)):
                            if row[j] and len(str(row[j]).strip()) > 10:  # Institute names are long
                                record['college_name'] = str(row[j]).strip()
                                break
                        # Course should be after institute
                        for j in range(i+1, min(len(row), i+4)):
                            if row[j] and ('MD' in str(row[j]) or 'MS' in str(row[j])):
                                record['course'] = str(row[j]).strip()
                                break
                        # Category might be available
                        for j in range(i+1, min(len(row), i+5)):
                            if row[j] and str(row[j]).strip() in ['GENERAL', 'OBC', 'SC', 'ST', 'EWS']:
                                record['category'] = str(row[j]).strip()
                                break
                        break
            
            # Set defaults
            record['year'] = 2024
            record['round'] = 3  # This is Round 3 data
            
            return record if 'rank' in record and 'college_name' in record else None
            
        except Exception as e:
            print(f"Error parsing all india row: {e}")
            return None
    
    def parse_all_india_text(self, text):
        """Parse All India quota data from text"""
        records = []
        lines = text.split('\n')
        
        for line in lines:
            # Pattern for All India entries
            pattern = r'(\d+)\s+(AI|IP|DU)\s+([^M]+)(M\.[DS]\..+?)(?:Reported|Not\s+Reported|Seat\s+Surrendered)'
            match = re.search(pattern, line)
            
            if match:
                record = {
                    'rank': int(match.group(1)),
                    'quota': match.group(2),
                    'college_name': match.group(3).strip(),
                    'course': match.group(4).strip(),
                    'year': 2024,
                    'round': 1
                }
                records.append(record)
        
        return records
    
    def insert_records(self, records):
        """Insert records into database in batches to prevent memory issues"""
        batch_size = 100
        total_inserted = 0
        total_skipped = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            batch_inserted = 0
            batch_skipped = 0
            
            for record in batch:
                try:
                    self.cursor.execute('''
                    INSERT INTO counselling_data 
                    (year, round, rank, quota, state, college_name, course, 
                     category, sub_category, gender, physically_handicapped, 
                     marks_obtained, max_marks, status, date_of_admission)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        record.get('year', 2024),
                        record.get('round', 1),
                        record.get('rank'),
                        record.get('quota'),
                        record.get('state'),
                        record.get('college_name'),
                        record.get('course'),
                        record.get('category'),
                        record.get('sub_category'),
                        record.get('gender'),
                        record.get('physically_handicapped'),
                        record.get('marks_obtained'),
                        record.get('max_marks'),
                        record.get('status'),
                        record.get('date_of_admission')
                    ))
                    batch_inserted += 1
                except psycopg2.IntegrityError:
                    batch_skipped += 1
                    continue
            
            # Commit batch
            self.conn.commit()
            total_inserted += batch_inserted
            total_skipped += batch_skipped
            
            # Progress update
            if len(records) > batch_size:
                progress = min((i + batch_size) / len(records) * 100, 100)
                print(f"  Progress: {progress:.1f}% - Batch: {batch_inserted} inserted, {batch_skipped} skipped")
        
        print(f"  Total: {total_inserted} records inserted, {total_skipped} duplicates skipped")
        return total_inserted
    
    def process_pdf_file(self, pdf_path, file_type='auto'):
        """Main method to process any PDF file"""
        print(f"Processing file: {pdf_path}")
        
        # Get just the filename for database storage
        filename = os.path.basename(pdf_path)
        
        # Check if file already processed
        self.cursor.execute('SELECT * FROM processed_files WHERE filename = %s', (filename,))
        if self.cursor.fetchone():
            print(f"File {filename} already processed. Skipping...")
            return []
        
        # Check if file exists
        if not os.path.exists(pdf_path):
            print(f"File not found: {pdf_path}")
            return []
        
        # Determine file type
        if file_type == 'auto':
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    if pdf.pages:
                        text = pdf.pages[0].extract_text() or ""
                        if ('State College Name' in text or 
                            'State Quota' in text or 
                            'Andhra Pradesh' in text):
                            file_type = 'state'
                        elif ('Round 1 Round 2 Round 3' in text or 
                              'Counselling Seats Allotment' in text or
                              'Allotted Quota' in text or
                              'Round' in filename):
                            file_type = 'all_india'
                        else:
                            file_type = 'all_india'  # Default fallback
            except Exception as e:
                print(f"Error reading file {pdf_path}: {e}")
                return []
        
        # Process based on type and insert in batches
        try:
            if file_type == 'state':
                record_generator = self.process_state_quota_pdf(pdf_path)
            else:
                record_generator = self.process_all_india_pdf(pdf_path)
            
            # Process records in batches to prevent memory issues
            batch_size = 100
            current_batch = []
            total_records = 0
            
            for record in record_generator:
                current_batch.append(record)
                
                # When batch is full, insert and commit
                if len(current_batch) >= batch_size:
                    inserted_count = self.insert_records(current_batch)
                    total_records += inserted_count
                    current_batch = []
                    print(f"    Batch processed: {inserted_count} records inserted")
            
            # Insert remaining records in the last batch
            if current_batch:
                inserted_count = self.insert_records(current_batch)
                total_records += inserted_count
                print(f"    Final batch processed: {inserted_count} records inserted")
            
            # Log processed file
            if total_records > 0:
                self.cursor.execute('''
                INSERT INTO processed_files (filename, file_type, records_count)
                VALUES (%s, %s, %s)
                ''', (filename, file_type, total_records))
                self.conn.commit()
                
                print(f"Successfully processed {total_records} records from {filename}")
                return total_records
            else:
                print(f"No records found in {filename}")
                return 0
                
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            return 0
    
    def get_eligible_colleges(self, rank, category=None, quota=None):
        """Get eligible colleges based on rank"""
        query = '''
        SELECT DISTINCT college_name, course, quota, rank as cutoff_rank, 
               category, round, year
        FROM counselling_data
        WHERE rank <= %s
        '''
        params = [rank]
        
        if category:
            query += ' AND category = %s'
            params.append(category)
        
        if quota:
            query += ' AND quota = %s'
            params.append(quota)
        
        query += ' ORDER BY rank DESC'
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
    def get_best_colleges_for_rank(self, rank, category=None, quota=None, limit=20):
        """Get the best (lowest cutoff) colleges for a given rank"""
        query = '''
        SELECT DISTINCT college_name, course, quota, rank as cutoff_rank, 
               category, round, year
        FROM counselling_data
        WHERE rank <= %s
        '''
        params = [rank]
        
        if category:
            query += ' AND category = %s'
            params.append(category)
        
        if quota:
            query += ' AND quota = %s'
            params.append(quota)
        
        query += ' ORDER BY rank ASC LIMIT %s'
        params.append(limit)
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
    def get_statistics(self):
        """Get database statistics"""
        stats = {}
        
        # Total records
        self.cursor.execute('SELECT COUNT(*) FROM counselling_data')
        stats['total_records'] = self.cursor.fetchone()[0]
        
        # Records by quota
        self.cursor.execute('''
        SELECT quota, COUNT(*) FROM counselling_data 
        GROUP BY quota
        ''')
        stats['by_quota'] = dict(self.cursor.fetchall())
        
        # Records by category
        self.cursor.execute('''
        SELECT category, COUNT(*) FROM counselling_data 
        WHERE category IS NOT NULL
        GROUP BY category
        ''')
        stats['by_category'] = dict(self.cursor.fetchall())
        
        # Unique colleges
        self.cursor.execute('SELECT COUNT(DISTINCT college_name) FROM counselling_data')
        stats['unique_colleges'] = self.cursor.fetchone()[0]
        
        # Unique courses
        self.cursor.execute('SELECT COUNT(DISTINCT course) FROM counselling_data')
        stats['unique_courses'] = self.cursor.fetchone()[0]
        
        return stats
    
    def export_to_json(self, output_file='counselling_data.json'):
        """Export database to JSON for web use"""
        self.cursor.execute('''
        SELECT DISTINCT college_name, course, quota, 
               MIN(rank) as cutoff_rank, category, round, year
        FROM counselling_data
        GROUP BY college_name, course, quota, category, round, year
        ORDER BY cutoff_rank DESC
        ''')
        
        data = []
        for row in self.cursor.fetchall():
            data.append({
                'college': row[0],
                'college_name': row[0],  # Add alias for compatibility
                'course': row[1],
                'quota': row[2],
                'cutoffRank': row[3],  # Use consistent naming
                'lastRank': row[3],    # Keep for backward compatibility
                'category': row[4] or 'GENERAL',
                'round': row[5],
                'year': row[6]
            })
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Data exported to {output_file}")
        return data
    
    def process_all_pdfs_in_folder(self, folder_path='pdfs'):
        """Process all PDF files in the specified folder"""
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            return {}
        
        # Get all PDF files in the folder
        pdf_pattern = os.path.join(folder_path, '*.pdf')
        pdf_files = glob.glob(pdf_pattern)
        
        if not pdf_files:
            print(f"No PDF files found in {folder_path}")
            return {}
        
        print(f"Found {len(pdf_files)} PDF files in {folder_path}")
        
        processing_results = {}
        total_records = 0
        
        for pdf_file in pdf_files:
            try:
                records = self.process_pdf_file(pdf_file)
                processing_results[os.path.basename(pdf_file)] = {
                    'records_count': len(records) if records else 0,
                    'status': 'success' if records else 'no_data'
                }
                total_records += len(records) if records else 0
            except Exception as e:
                print(f"Failed to process {pdf_file}: {e}")
                processing_results[os.path.basename(pdf_file)] = {
                    'records_count': 0,
                    'status': 'error',
                    'error': str(e)
                }
        
        print(f"\n=== Processing Summary ===")
        print(f"Total files processed: {len(pdf_files)}")
        print(f"Total records extracted: {total_records}")
        
        for filename, result in processing_results.items():
            status_icon = "✅" if result['status'] == 'success' else "❌" if result['status'] == 'error' else "⚠️"
            print(f"{status_icon} {filename}: {result['records_count']} records ({result['status']})")
        
        return processing_results
    
    def clear_database(self):
        """Clear all data from the database (use with caution!)"""
        print("⚠️  WARNING: This will delete ALL data from the database!")
        confirm = input("Type 'YES' to confirm: ")
        if confirm == 'YES':
            self.cursor.execute('DELETE FROM counselling_data')
            self.cursor.execute('DELETE FROM processed_files')
            self.conn.commit()
            print("Database cleared successfully!")
        else:
            print("Database clear operation cancelled.")
    
    def test_connection(self):
        """Test database connection"""
        try:
            self.cursor.execute('SELECT 1')
            result = self.cursor.fetchone()
            if result:
                print("✅ PostgreSQL connection successful!")
                return True
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# Example usage
if __name__ == "__main__":
    import sys
    
    # Initialize processor
    processor = NEETPGDataProcessor()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'clear':
            processor.clear_database()
            processor.close()
            sys.exit(0)
        elif command == 'stats':
            stats = processor.get_statistics()
            print("\n=== Database Statistics ===")
            print(f"Total Records: {stats['total_records']}")
            print(f"Unique Colleges: {stats['unique_colleges']}")
            print(f"Unique Courses: {stats['unique_courses']}")
            print(f"By Quota: {stats['by_quota']}")
            print(f"By Category: {stats['by_category']}")
            processor.close()
            sys.exit(0)
        elif command == 'export':
            print("Exporting data to JSON...")
            processor.export_to_json()
            processor.close()
            sys.exit(0)
        elif command == 'test':
            processor.test_connection()
            processor.close()
            sys.exit(0)
    
    # Test database connection first
    if not processor.test_connection():
        print("❌ Cannot proceed without database connection!")
        processor.close()
        sys.exit(1)
    
    # Default: Process all PDF files in the pdfs folder
    print("Starting to process all PDFs in the 'pdfs' folder...")
    print("This will process files one by one with memory-efficient batching...")
    processing_results = processor.process_all_pdfs_in_folder('pdfs')
    
    # Get statistics
    stats = processor.get_statistics()
    print("\n=== Database Statistics ===")
    print(f"Total Records: {stats['total_records']}")
    print(f"Unique Colleges: {stats['unique_colleges']}")
    print(f"Unique Courses: {stats['unique_courses']}")
    print(f"By Quota: {stats['by_quota']}")
    print(f"By Category: {stats['by_category']}")
    
    # Example: Get eligible colleges for a rank
    rank = 5000
    eligible = processor.get_eligible_colleges(rank)
    print(f"\n=== All Eligible Colleges for Rank {rank} ===")
    print(f"Total eligible colleges: {len(eligible)}")
    
    # Get best colleges (lowest cutoff ranks first)
    best_colleges = processor.get_best_colleges_for_rank(rank, limit=10)
    print(f"\n=== Top 10 Best Colleges for Rank {rank} (Lowest Cutoffs) ===")
    for college in best_colleges:
        print(f"- {college[0]}: {college[1]} (Cutoff: {college[3]})")
    
    # Export to JSON for web use
    print("\nExporting data to JSON...")
    processor.export_to_json()
    
    # Close connection
    processor.close()
    
    print("\n=== Processing Complete ===")
    print("All PDFs have been processed and data is ready for use!")
    print("\nUsage options:")
    print("  python pdf_uploader.py          - Process all PDFs")
    print("  python pdf_uploader.py test     - Test PostgreSQL connection")
    print("  python pdf_uploader.py stats    - Show database statistics")
    print("  python pdf_uploader.py export   - Export data to JSON")
    print("  python pdf_uploader.py clear    - Clear database (use with caution!)")
    print("\nDatabase Configuration:")
    print(f"  Host: {processor.db_config['host']}")
    print(f"  Database: {processor.db_config['database']}")
    print(f"  User: {processor.db_config['user']}")
    print(f"  Port: {processor.db_config['port']}")