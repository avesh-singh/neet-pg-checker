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
        self.setup_abbreviation_mappings()
    
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
            student_name TEXT,
            date_of_birth TEXT,
            exam_name_roll TEXT,
            pg_teacher TEXT,
            stipend_amount INTEGER,
            student_regn_no TEXT,
            registered_council TEXT,
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
            records_count INTEGER,
            verification_status TEXT DEFAULT 'pending',
            verified_at TIMESTAMP,
            verified_by TEXT,
            sample_size INTEGER
        )
        ''')
        
        # Table for verification records (sampling-based)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS verification_records (
            id SERIAL PRIMARY KEY,
            counselling_data_id INTEGER REFERENCES counselling_data(id) ON DELETE CASCADE,
            processed_file_id INTEGER REFERENCES processed_files(id) ON DELETE CASCADE,
            page_number INTEGER NOT NULL,
            verification_status TEXT DEFAULT 'pending',
            verified_at TIMESTAMP,
            verified_by TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create indexes for verification table
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_verification_counselling_data ON verification_records(counselling_data_id)
        ''')
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_verification_processed_file ON verification_records(processed_file_id)
        ''')
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_verification_status ON verification_records(verification_status)
        ''')
        
        self.conn.commit()
    
    def setup_abbreviation_mappings(self):
        """Setup mappings for abbreviations found in PDFs"""
        # Quota mappings from legend
        self.quota_mappings = {
            'AI': 'All India',
            'IP': 'IP University Quota',
            'DU': 'Delhi University Quota',
            'AD': 'DNB Quota',
            'AF': 'Armed Forces Medical',
            'AM': 'Aligarh Muslim University',
            'BH': 'Banaras Hindu University',
            'JM': 'Jain Minority Quota',
            'MM': 'Muslim Minority Quota',
            'NR': 'Non-Resident Indian',
            'PS': 'Management/Paid Seats Quota'
        }
        
        # Category mappings from legend
        self.category_mappings = {
            'BC': 'OBC',
            'BC PwD': 'OBC-PwD',
            'EW': 'EWS',
            'EW PwD': 'EWS-PwD',
            'GN': 'GENERAL',
            'GN PwD': 'GENERAL-PwD',
            'SC': 'SC',
            'SC PwD': 'SC-PwD',
            'ST': 'ST',
            'ST PwD': 'ST-PwD',
            'Open': 'GENERAL'
        }
    
    def normalize_quota(self, quota_str):
        """Normalize quota abbreviation to full form"""
        if not quota_str:
            return None
        quota_str = str(quota_str).strip()
        return self.quota_mappings.get(quota_str, quota_str)
    
    def normalize_category(self, category_str):
        """Normalize category abbreviation to standard form"""
        if not category_str:
            return 'GENERAL'
        category_str = str(category_str).strip()
        return self.category_mappings.get(category_str, category_str)

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
                                    record['_page_number'] = page_num + 1  # Add page tracking
                                    yield record
    
    def parse_state_quota_row(self, row):
        """Parse a row from state quota table"""
        try:
            # Based on state_pg.pdf structure (17 columns):
            # Col 0: State, Col 1: College Name, Col 2: Course, Col 3: Name of Student, 
            # Col 4: Gender, Col 5: DOB, Col 6: Admitted By, Col 7: Sub Category, 
            # Col 8: Physically Handicapped, Col 9: Exam Name/Roll, Col 10: Exam Rank, 
            # Col 11: Marks, Col 12: PG Teacher, Col 13: Stipend, Col 14: Student Regn, 
            # Col 15: Council, Col 16: Date of Admission
            
            if not row or len(row) < 11:
                return None
            
            record = {}
            
            # Extract state (column 0)
            if row[0] and str(row[0]).strip():
                record['state'] = str(row[0]).strip()
            
            # Extract college name (column 1) 
            if row[1] and str(row[1]).strip():
                record['college_name'] = str(row[1]).strip()
            
            # Extract course (column 2)
            if row[2] and str(row[2]).strip():
                course = str(row[2]).strip()
                # Normalize course names
                course = course.replace('MD - ', 'M.D. ').replace('MD/MS - ', 'M.D./M.S. ')
                record['course'] = course
            
            # Extract student name (column 3)
            if row[3] and str(row[3]).strip():
                record['student_name'] = str(row[3]).strip()
            
            # Extract gender (column 4)
            if row[4] and str(row[4]).strip():
                record['gender'] = str(row[4]).strip()
            
            # Extract date of birth (column 5)
            if row[5] and str(row[5]).strip():
                record['date_of_birth'] = str(row[5]).strip()
            
            # Extract quota info (column 6) - "Admitted By"
            if row[6] and str(row[6]).strip():
                quota = str(row[6]).strip()
                record['quota'] = self.normalize_quota(quota) or 'State Quota'
            
            # Extract category (column 7) - "Sub Category"  
            if row[7] and str(row[7]).strip():
                category = str(row[7]).strip()
                record['category'] = self.normalize_category(category)
            
            # Extract physically handicapped (column 8)
            if row[8] and str(row[8]).strip():
                record['physically_handicapped'] = str(row[8]).strip()
            
            # Extract exam name/roll (column 9)
            if row[9] and str(row[9]).strip():
                record['exam_name_roll'] = str(row[9]).strip()
            
            # Extract rank from column 10 - "Exam Rank AIR/State Rank"
            if row[10] and str(row[10]).strip():
                rank_text = str(row[10]).strip()
                # Extract numeric rank - could be like "25579" or "94638"
                rank_match = re.search(r'(\d{4,6})', rank_text)
                if rank_match:
                    record['rank'] = int(rank_match.group(1))
            
            # Extract marks (column 11) - "Marks Obtained/Maximum Marks"
            if row[11] and str(row[11]).strip():
                marks_text = str(row[11]).strip()
                marks_match = re.search(r'(\d+)\s*/\s*(\d+)', marks_text)
                if marks_match:
                    record['marks_obtained'] = int(marks_match.group(1))
                    record['max_marks'] = int(marks_match.group(2))
            
            # Extract PG teacher (column 12)
            if len(row) > 12 and row[12] and str(row[12]).strip():
                record['pg_teacher'] = str(row[12]).strip()
            
            # Extract stipend amount (column 13)
            if len(row) > 13 and row[13] and str(row[13]).strip():
                stipend_text = str(row[13]).strip()
                # Extract numeric stipend amount
                stipend_match = re.search(r'(\d+)', stipend_text)
                if stipend_match:
                    record['stipend_amount'] = int(stipend_match.group(1))
            
            # Extract student registration number (column 14)
            if len(row) > 14 and row[14] and str(row[14]).strip():
                record['student_regn_no'] = str(row[14]).strip()
            
            # Extract registered council (column 15)
            if len(row) > 15 and row[15] and str(row[15]).strip():
                record['registered_council'] = str(row[15]).strip()
            
            # Extract date of admission (column 16)
            if len(row) > 16 and row[16] and str(row[16]).strip():
                record['date_of_admission'] = str(row[16]).strip()
            
            # Set defaults
            record['year'] = 2024
            record['round'] = 1  # State quota is typically round 1
            record['status'] = 'Reported'  # State counselling data shows admitted students
            
            return record if 'rank' in record and record['rank'] else None
            
        except Exception as e:
            print(f"Error parsing state quota row: {e}")
            return None
    
    def process_all_india_pdf(self, pdf_path):
        """Process All India Quota PDF page by page to prevent memory issues"""
        # Determine PDF type based on filename and content
        filename = os.path.basename(pdf_path).lower()
        
        with pdfplumber.open(pdf_path) as pdf:
            # Check first page to determine format
            first_page_text = pdf.pages[0].extract_text() or ""
            
            # Determine if this is Round 3 multi-round format or single round format
            is_multi_round = ('Round 1 Round 2' in first_page_text or 
                             'round 3' in filename and 'final result' in filename.lower())
            
            # Determine round number from filename and content
            round_number = self.extract_round_number(filename)
            
            # Override round number based on content
            if 'stray' in first_page_text.lower():
                round_number = 5  # Stray rounds are typically Round 5
            
            for page_num, page in enumerate(pdf.pages):
                print(f"    Processing page {page_num + 1}/{len(pdf.pages)}")
                
                # Extract tables if present
                tables = page.extract_tables()
                
                if tables:
                    for table in tables:
                        if is_multi_round:
                            # Process multi-round format (Round 3 style)
                            records = self.parse_multi_round_table(table, round_number, page_num + 1)
                        else:
                            # Process single round format (Round 4/5 style)  
                            records = self.parse_single_round_table(table, round_number, page_num + 1)
                        
                        for record in records:
                            if record:
                                yield record
                else:
                    # Fallback to text extraction
                    text = page.extract_text()
                    records = self.parse_all_india_text(text, round_number, page_num + 1)
                    for record in records:
                        yield record
    
    def extract_round_number(self, filename):
        """Extract round number from filename"""
        filename_lower = filename.lower()
        if 'round 4' in filename_lower or 'pg_round_4' in filename_lower:
            return 4
        elif 'round 5' in filename_lower or 'stray' in filename_lower:
            return 5
        elif 'round 3' in filename_lower or 'pg_round_3' in filename_lower:
            return 3
        elif 'pg_round_4' in filename_lower:  # Special case for our test file
            return 4
        return 1  # Default
    
    def parse_multi_round_table(self, table, default_round, page_number=1):
        """Parse multi-round format table (Round 3 style)"""
        records = []
        
        # Skip header rows
        for i, row in enumerate(table):
            if i < 2:  # Skip header rows
                continue
                
            if not row or len(row) < 8:
                continue
            
            # Extract rank from first column
            rank = None
            if row[0] and str(row[0]).strip().isdigit():
                rank = int(str(row[0]).strip())
            else:
                continue  # Skip if no valid rank
            
            # Process each round's data in the row
            # Round 1: columns 1-5, Round 2: columns 6-10, Round 3: columns 11-15+
            round_configs = [
                (1, 1, 5),   # Round 1: columns 1-4
                (2, 5, 9),   # Round 2: columns 5-8  
                (3, 9, 13),  # Round 3: columns 9-12
            ]
            
            for round_num, start_col, end_col in round_configs:
                if len(row) > start_col:
                    record = self.extract_round_data(row, rank, round_num, start_col, end_col)
                    if record:
                        record['_page_number'] = page_number
                        records.append(record)
        
        return records
    
    def parse_single_round_table(self, table, round_number, page_number=1):
        """Parse single round format table (Round 4/5 style)"""
        records = []
        
        # Skip header row
        for i, row in enumerate(table):
            if i < 1:  # Skip header row
                continue
                
            if not row or len(row) < 5:
                continue
            
            record = self.parse_single_round_row(row, round_number)
            if record:
                record['_page_number'] = page_number
                records.append(record)
        
        return records
    
    def extract_round_data(self, row, rank, round_num, start_col, end_col):
        """Extract data for a specific round from multi-round row"""
        try:
            # Check if we have data for this round (quota should not be empty)
            if start_col >= len(row) or not row[start_col] or str(row[start_col]).strip() in ['-', '']:
                return None
                
            record = {
                'rank': rank,
                'round': round_num,
                'year': 2024
            }
            
            # Extract quota (typically first column of round data)
            if start_col < len(row) and row[start_col]:
                quota = str(row[start_col]).strip()
                record['quota'] = self.normalize_quota(quota)
            
            # Extract college (typically second column of round data)
            if start_col + 1 < len(row) and row[start_col + 1]:
                college = str(row[start_col + 1]).strip()
                if college and college not in ['-', '']:
                    record['college_name'] = college
            
            # Extract course (typically third column of round data)
            if start_col + 2 < len(row) and row[start_col + 2]:
                course = str(row[start_col + 2]).strip()
                if course and course not in ['-', '']:
                    record['course'] = course
            
            # Extract status/remarks (typically fourth column of round data)
            if start_col + 3 < len(row) and row[start_col + 3]:
                status = str(row[start_col + 3]).strip()
                if status and status not in ['-', '']:
                    record['status'] = status
                    
            # Extract category if available (typically fifth column of round data)
            if start_col + 4 < len(row) and row[start_col + 4]:
                category = str(row[start_col + 4]).strip()
                if category and category not in ['-', '']:
                    record['category'] = self.normalize_category(category)
            
            # Only return record if we have essential data
            if 'college_name' in record and 'course' in record:
                return record
                
            return None
            
        except Exception as e:
            print(f"Error extracting round {round_num} data: {e}")
            return None
    
    def parse_single_round_row(self, row, round_number):
        """Parse single round format row (Round 4/5 style)"""
        try:
            record = {
                'round': round_number,
                'year': 2024
            }
            
            # Extract rank (column 1)
            if row[1] and str(row[1]).strip().isdigit():
                record['rank'] = int(str(row[1]).strip())
            else:
                return None
            
            # Extract quota (column 2)
            if row[2] and str(row[2]).strip():
                quota = str(row[2]).strip()
                record['quota'] = self.normalize_quota(quota)
            
            # Extract college (column 3)
            if row[3] and str(row[3]).strip():
                college = str(row[3]).strip()
                record['college_name'] = college
            
            # Extract course (column 4)
            if row[4] and str(row[4]).strip():
                course = str(row[4]).strip()
                record['course'] = course
            
            # Extract category (column 5 or 6)
            category_col = 5 if len(row) > 5 else None
            if category_col and category_col < len(row) and row[category_col]:
                category = str(row[category_col]).strip()
                if category and category not in ['-', '']:
                    record['category'] = self.normalize_category(category)
            
            # Extract remarks/status (column 6 or 7)
            remarks_col = 6 if len(row) > 6 else None
            if remarks_col and remarks_col < len(row) and row[remarks_col]:
                status = str(row[remarks_col]).strip()
                if status and status not in ['-', '']:
                    record['status'] = status
            
            # Only return record if we have essential data
            if 'rank' in record and 'college_name' in record and 'course' in record:
                return record
                
            return None
            
        except Exception as e:
            print(f"Error parsing single round row: {e}")
            return None

    def parse_all_india_text(self, text, round_number=1, page_number=1):
        """Parse All India quota data from text (fallback method)"""
        records = []
        lines = text.split('\n')
        
        for line in lines:
            # Pattern for All India entries
            patterns = [
                # Pattern for simple format: rank quota college course status
                r'(\d+)\s+(AI|IP|DU|All India)\s+([^M]+?)(M\.[DS]\..+?)(?:Reported|Not\s+Reported|Seat\s+Surrendered|Allotted)',
                # Pattern for more complex format
                r'(\d+)\s+(\w+)\s+(.+?)\s+(M\.[DS]\.\s*.+?)(?:Open|General|OBC|SC|ST|EWS|Allotted)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    record = {
                        'rank': int(match.group(1)),
                        'quota': self.normalize_quota(match.group(2)),
                        'college_name': match.group(3).strip(),
                        'course': match.group(4).strip(),
                        'year': 2024,
                        'round': round_number,
                        '_page_number': page_number
                    }
                    records.append(record)
                    break
        
        return records
    
    def insert_records_with_verification(self, records, processed_file_id, enable_verification=False, sample_rate=0.1):
        """Insert records and optionally create verification records for sampling"""
        batch_size = 100
        total_inserted = 0
        total_skipped = 0
        verification_records = []
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            batch_inserted = 0
            batch_skipped = 0
            
            for record in batch:
                try:
                    # Insert main record
                    self.cursor.execute('''
                    INSERT INTO counselling_data 
                    (year, round, rank, quota, state, college_name, course, 
                     category, sub_category, gender, physically_handicapped, 
                     marks_obtained, max_marks, status, date_of_admission,
                     student_name, date_of_birth, exam_name_roll, pg_teacher,
                     stipend_amount, student_regn_no, registered_council)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
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
                        record.get('date_of_admission'),
                        record.get('student_name'),
                        record.get('date_of_birth'),
                        record.get('exam_name_roll'),
                        record.get('pg_teacher'),
                        record.get('stipend_amount'),
                        record.get('student_regn_no'),
                        record.get('registered_council')
                    ))
                    
                    record_id = self.cursor.fetchone()[0]
                    batch_inserted += 1
                    
                    # Create verification record if enabled and sampling matches
                    if enable_verification and record.get('_page_number') and (len(verification_records) == 0 or 
                        (batch_inserted + total_inserted) % int(1/sample_rate) == 0):
                        verification_records.append({
                            'counselling_data_id': record_id,
                            'processed_file_id': processed_file_id,
                            'page_number': record.get('_page_number')
                        })
                        
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
        
        # Insert verification records if any
        if verification_records and enable_verification:
            self.insert_verification_records(verification_records)
            print(f"  Created {len(verification_records)} verification records for sampling")
        
        print(f"  Total: {total_inserted} records inserted, {total_skipped} duplicates skipped")
        return total_inserted
    
    def insert_verification_records(self, verification_records):
        """Insert verification records in batch"""
        for vr in verification_records:
            try:
                self.cursor.execute('''
                INSERT INTO verification_records 
                (counselling_data_id, processed_file_id, page_number)
                VALUES (%s, %s, %s)
                ''', (vr['counselling_data_id'], vr['processed_file_id'], vr['page_number']))
            except Exception as e:
                print(f"Error inserting verification record: {e}")
        self.conn.commit()
    
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
                     marks_obtained, max_marks, status, date_of_admission,
                     student_name, date_of_birth, exam_name_roll, pg_teacher,
                     stipend_amount, student_regn_no, registered_council)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        record.get('date_of_admission'),
                        record.get('student_name'),
                        record.get('date_of_birth'),
                        record.get('exam_name_roll'),
                        record.get('pg_teacher'),
                        record.get('stipend_amount'),
                        record.get('student_regn_no'),
                        record.get('registered_council')
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
    
    def process_pdf_file(self, pdf_path, file_type='state', enable_verification=False, sample_rate=0.1):
        """Main method to process any PDF file
        
        Args:
            pdf_path (str): Path to the PDF file
            file_type (str): Format type - 'state' for state quota format, 'all_india' for All India quota format
            enable_verification (bool): Whether to create verification records for sampling
            sample_rate (float): Fraction of records to include in verification sampling (0.1 = 10%)
        """
        print(f"Processing file: {pdf_path}")
        print(f"Using format: {file_type}")
        
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
        
        # Validate file_type parameter
        if file_type not in ['state', 'all_india']:
            print(f"Invalid file_type: {file_type}. Must be 'state' or 'all_india'")
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
            
            # Log processed file and get ID for verification records
            if total_records > 0:
                self.cursor.execute('''
                INSERT INTO processed_files (filename, file_type, records_count, sample_size)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                ''', (filename, file_type, total_records, int(total_records * sample_rate) if enable_verification else None))
                processed_file_id = self.cursor.fetchone()[0]
                
                # If verification is enabled, process records again with verification
                if enable_verification:
                    print(f"Creating verification records with {sample_rate*100:.1f}% sampling rate...")
                    # Re-process for verification records
                    verification_count = 0
                    if file_type == 'state':
                        record_generator = self.process_state_quota_pdf(pdf_path)
                    else:
                        record_generator = self.process_all_india_pdf(pdf_path)
                    
                    # Collect all records first to sample properly
                    all_records = list(record_generator)
                    sample_indices = list(range(0, len(all_records), int(1/sample_rate)))
                    
                    # Get counselling_data IDs for sampled records
                    for idx in sample_indices:
                        if idx < len(all_records):
                            record = all_records[idx]
                            # Find the counselling_data record ID
                            self.cursor.execute('''
                            SELECT id FROM counselling_data 
                            WHERE rank = %s AND college_name = %s AND course = %s 
                            ORDER BY id DESC LIMIT 1
                            ''', (record.get('rank'), record.get('college_name'), record.get('course')))
                            
                            result = self.cursor.fetchone()
                            if result and record.get('_page_number'):
                                self.cursor.execute('''
                                INSERT INTO verification_records 
                                (counselling_data_id, processed_file_id, page_number)
                                VALUES (%s, %s, %s)
                                ''', (result[0], processed_file_id, record.get('_page_number')))
                                verification_count += 1
                    
                    self.conn.commit()
                    print(f"Created {verification_count} verification records for sampling")
                
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
    
    def get_detailed_status(self):
        """Get comprehensive database status with completeness analysis"""
        print("=== Comprehensive Database Status ===")
        
        # Get basic statistics
        stats = self.get_statistics()
        print(f"\n=== Overall Statistics ===")
        print(f"Total Records: {stats['total_records']}")
        print(f"Unique Colleges: {stats['unique_colleges']}")
        print(f"Unique Courses: {stats['unique_courses']}")
        
        print(f"\n=== Distribution by Quota ===")
        for quota, count in stats['by_quota'].items():
            print(f"  {quota}: {count}")
        
        print(f"\n=== Distribution by Category ===")
        for category, count in stats['by_category'].items():
            print(f"  {category}: {count}")
        
        # Round-wise distribution
        print(f"\n=== Distribution by Round ===")
        self.cursor.execute('''
        SELECT round, COUNT(*) as count 
        FROM counselling_data 
        GROUP BY round 
        ORDER BY round
        ''')
        
        for round_num, count in self.cursor.fetchall():
            print(f"  Round {round_num}: {count}")
        
        # Data completeness check
        print(f"\n=== Data Completeness ===")
        
        # Essential fields
        self.cursor.execute('SELECT COUNT(*) FROM counselling_data WHERE rank IS NOT NULL')
        rank_complete = self.cursor.fetchone()[0]
        print(f"Records with rank: {rank_complete}/{stats['total_records']} ({rank_complete/stats['total_records']*100:.1f}%)")
        
        self.cursor.execute('SELECT COUNT(*) FROM counselling_data WHERE college_name IS NOT NULL')
        college_complete = self.cursor.fetchone()[0]
        print(f"Records with college: {college_complete}/{stats['total_records']} ({college_complete/stats['total_records']*100:.1f}%)")
        
        self.cursor.execute('SELECT COUNT(*) FROM counselling_data WHERE course IS NOT NULL')
        course_complete = self.cursor.fetchone()[0]
        print(f"Records with course: {course_complete}/{stats['total_records']} ({course_complete/stats['total_records']*100:.1f}%)")
        
        # State-specific fields
        self.cursor.execute('SELECT COUNT(*) FROM counselling_data WHERE student_name IS NOT NULL')
        name_complete = self.cursor.fetchone()[0]
        print(f"Records with student name: {name_complete}/{stats['total_records']} ({name_complete/stats['total_records']*100:.1f}%)")
        
        self.cursor.execute('SELECT COUNT(*) FROM counselling_data WHERE pg_teacher IS NOT NULL')
        teacher_complete = self.cursor.fetchone()[0]
        print(f"Records with PG teacher: {teacher_complete}/{stats['total_records']} ({teacher_complete/stats['total_records']*100:.1f}%)")
        
        # Sample records from each type
        print(f"\n=== Sample Records by Data Source ===")
        
        # All India sample
        self.cursor.execute('''
        SELECT rank, college_name, course, quota, round FROM counselling_data 
        WHERE quota = 'All India' ORDER BY rank LIMIT 2
        ''')
        ai_samples = self.cursor.fetchall()
        if ai_samples:
            print(f"\n📊 All India Sample:")
            for rank, college, course, quota, round_num in ai_samples:
                print(f"  Rank {rank} (Round {round_num}): {college[:40]}...")
                print(f"    Course: {course[:40]}...")
        
        # State sample
        self.cursor.execute('''
        SELECT rank, student_name, college_name, course, pg_teacher FROM counselling_data 
        WHERE quota = 'State Quota' ORDER BY rank LIMIT 2
        ''')
        state_samples = self.cursor.fetchall()
        if state_samples:
            print(f"\n🏥 State Quota Sample:")
            for rank, name, college, course, teacher in state_samples:
                print(f"  {name} (Rank {rank})")
                print(f"    College: {college[:40]}...")
                print(f"    Course: {course[:40]}...")
                print(f"    PG Teacher: {teacher}")
        
        # DNB sample  
        self.cursor.execute('''
        SELECT rank, college_name, course, quota, round FROM counselling_data 
        WHERE quota = 'DNB Quota' ORDER BY rank LIMIT 2
        ''')
        dnb_samples = self.cursor.fetchall()
        if dnb_samples:
            print(f"\n🏥 DNB Quota Sample:")
            for rank, college, course, quota, round_num in dnb_samples:
                print(f"  Rank {rank} (Round {round_num}): {college[:40]}...")
                print(f"    Course: {course[:40]}...")
        
        # Processed files check
        print(f"\n=== Processed Files ===")
        self.cursor.execute('SELECT filename, records_count FROM processed_files ORDER BY records_count DESC')
        processed = self.cursor.fetchall()
        if processed:
            for filename, count in processed:
                print(f"  ✅ {filename}: {count} records")
        else:
            print("  ℹ️ No processed files logged")
        
        return stats
    
    def validate_state_data(self):
        """Validate and check for issues in the imported state counselling data"""
        print("=== Validating State Counselling Data ===")
        
        # Check for missing critical fields in state data
        print("\n=== Missing Field Analysis ===")
        
        # Check state records with missing fields
        self.cursor.execute('''
        SELECT COUNT(*) FROM counselling_data 
        WHERE quota = 'State Quota' AND student_name IS NULL
        ''')
        missing_names = self.cursor.fetchone()[0]
        print(f"State records missing student names: {missing_names}")
        
        self.cursor.execute('''
        SELECT COUNT(*) FROM counselling_data 
        WHERE quota = 'State Quota' AND date_of_birth IS NULL
        ''')
        missing_dob = self.cursor.fetchone()[0]
        print(f"State records missing date of birth: {missing_dob}")
        
        self.cursor.execute('''
        SELECT COUNT(*) FROM counselling_data 
        WHERE quota = 'State Quota' AND pg_teacher IS NULL
        ''')
        missing_teacher = self.cursor.fetchone()[0]
        print(f"State records missing PG teacher: {missing_teacher}")
        
        self.cursor.execute('''
        SELECT COUNT(*) FROM counselling_data 
        WHERE quota = 'State Quota' AND stipend_amount IS NULL
        ''')
        missing_stipend = self.cursor.fetchone()[0]
        print(f"State records missing stipend: {missing_stipend}")
        
        # Check course normalization issues
        print(f"\n=== Course Name Analysis ===")
        self.cursor.execute('''
        SELECT DISTINCT course FROM counselling_data 
        WHERE quota = 'State Quota'
        ORDER BY course
        ''')
        
        state_courses = self.cursor.fetchall()
        print(f"Number of unique courses in state data: {len(state_courses)}")
        
        # Check for inconsistencies
        problematic_courses = []
        for (course,) in state_courses:
            if course and ('MD - ' in course or 'MD/MS - ' in course):
                problematic_courses.append(course)
        
        if problematic_courses:
            print(f"\n❌ Found {len(problematic_courses)} courses with inconsistent naming:")
            for course in problematic_courses[:5]:  # Show first 5
                print(f"  - {course}")
            if len(problematic_courses) > 5:
                print(f"  ... and {len(problematic_courses) - 5} more")
        else:
            print("✅ All course names appear properly normalized")
        
        # Check category consistency  
        print(f"\n=== Category Analysis ===")
        self.cursor.execute('''
        SELECT category, COUNT(*) FROM counselling_data 
        WHERE quota = 'State Quota'
        GROUP BY category 
        ORDER BY COUNT(*) DESC
        ''')
        
        state_categories = self.cursor.fetchall()
        print("Category distribution in state data:")
        for category, count in state_categories:
            print(f"  {category}: {count}")
        
        # Check rank ranges
        print(f"\n=== Rank Range Analysis ===")
        self.cursor.execute('''
        SELECT MIN(rank), MAX(rank), AVG(rank) FROM counselling_data 
        WHERE quota = 'State Quota'
        ''')
        
        result = self.cursor.fetchone()
        if result and result[0]:
            min_rank, max_rank, avg_rank = result
            print(f"State quota rank range: {min_rank} to {max_rank}")
            print(f"Average rank: {avg_rank:.0f}")
        
        # Compare with All India ranks
        self.cursor.execute('''
        SELECT MIN(rank), MAX(rank), AVG(rank) FROM counselling_data 
        WHERE quota = 'All India'
        ''')
        
        ai_result = self.cursor.fetchone()
        if ai_result and ai_result[0]:
            ai_min, ai_max, ai_avg = ai_result
            print(f"All India rank range: {ai_min} to {ai_max}")
            print(f"Average rank: {ai_avg:.0f}")
        
        # Check for duplicates
        print(f"\n=== Duplicate Analysis ===")
        self.cursor.execute('''
        SELECT student_name, COUNT(*) as cnt FROM counselling_data 
        WHERE student_name IS NOT NULL
        GROUP BY student_name 
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        ''')
        
        duplicates = self.cursor.fetchall()
        if duplicates:
            print(f"❌ Found {len(duplicates)} duplicate student names:")
            for name, count in duplicates[:3]:
                print(f"  {name}: {count} records")
        else:
            print("✅ No duplicate student names found")
        
        # Check gender distribution
        print(f"\n=== Gender Distribution ===")
        self.cursor.execute('''
        SELECT gender, COUNT(*) FROM counselling_data 
        WHERE gender IS NOT NULL
        GROUP BY gender
        ''')
        
        gender_dist = self.cursor.fetchall()
        if gender_dist:
            for gender, count in gender_dist:
                print(f"  {gender}: {count}")
        else:
            print("  No gender data found")
        
        print("\n=== Validation Complete ===")
    
    def show_verification_status(self):
        """Show verification status and pending records"""
        print("=== Verification Status ===")
        
        # Check if verification tables exist
        try:
            self.cursor.execute('''
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'verification_records'
            ''')
            if self.cursor.fetchone()[0] == 0:
                print("❌ Verification tables not found. Run migrations first.")
                return
        except Exception as e:
            print(f"❌ Error checking verification tables: {e}")
            return
        
        # Files with verification status
        print("\n=== Processed Files Verification Status ===")
        self.cursor.execute('''
        SELECT f.filename, f.records_count, f.sample_size, f.verification_status,
               COUNT(vr.id) as verification_records,
               COUNT(CASE WHEN vr.verification_status = 'verified' THEN 1 END) as verified_count,
               COUNT(CASE WHEN vr.verification_status = 'rejected' THEN 1 END) as rejected_count
        FROM processed_files f
        LEFT JOIN verification_records vr ON f.id = vr.processed_file_id
        GROUP BY f.id, f.filename, f.records_count, f.sample_size, f.verification_status
        ORDER BY f.processed_date DESC
        ''')
        
        file_results = self.cursor.fetchall()
        if file_results:
            for filename, records_count, sample_size, status, vr_count, verified, rejected in file_results:
                print(f"\n📄 {filename}")
                print(f"  Records: {records_count}")
                print(f"  Sample Size: {sample_size or 'No sample'}")
                print(f"  File Status: {status}")
                if vr_count > 0:
                    progress = round((verified / vr_count) * 100) if vr_count > 0 else 0
                    print(f"  Verification: {verified}/{vr_count} verified ({progress}%), {rejected} rejected")
                else:
                    print("  Verification: No verification records")
        else:
            print("No processed files found")
        
        # Overall verification statistics
        print("\n=== Overall Verification Statistics ===")
        self.cursor.execute('''
        SELECT verification_status, COUNT(*) FROM verification_records 
        GROUP BY verification_status
        ''')
        vr_stats = self.cursor.fetchall()
        if vr_stats:
            for status, count in vr_stats:
                print(f"  {status}: {count}")
        else:
            print("  No verification records found")
        
        # Pending verification records sample
        print("\n=== Pending Verification Records (Sample) ===")
        self.cursor.execute('''
        SELECT vr.id, vr.page_number, cd.rank, cd.college_name, cd.course, pf.filename
        FROM verification_records vr
        JOIN counselling_data cd ON vr.counselling_data_id = cd.id
        JOIN processed_files pf ON vr.processed_file_id = pf.id
        WHERE vr.verification_status = 'pending'
        ORDER BY vr.created_at DESC
        LIMIT 5
        ''')
        
        pending_records = self.cursor.fetchall()
        if pending_records:
            for vr_id, page_num, rank, college, course, filename in pending_records:
                print(f"  ID {vr_id}: Page {page_num} in {filename}")
                print(f"    Rank {rank}: {college[:50]}...")
                print(f"    Course: {course[:50]}...")
        else:
            print("  No pending verification records")
        
        print("\n=== Usage ===")
        print("To import with verification: python pdf_uploader.py import <file> <format> --verify")
        print("To create samples for existing files: Use the web interface at /admin/verification")
    
    def batch_import_pdfs(self, pdfs_dir, pdf_files=None):
        """Import multiple PDFs from a directory with progress tracking"""
        if pdf_files is None:
            pdf_files = [
                '104. Round 3 Final Result_XENMENTOR (1).pdf',
                '121. Round 4 Final Result (1)_XENMENTOR.pdf', 
                '137. Round 5 Special Stray Final Result (1)_XENMENTOR.pdf',
                'DOC-20240822-WA0000.pdf'
            ]
        
        print(f"=== Batch PDF Import from {pdfs_dir} ===")
        
        # Get initial statistics
        stats_initial = self.get_statistics()
        print(f"Initial records in database: {stats_initial['total_records']}")
        print()
        
        successful_imports = 0
        total_new_records = 0
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdfs_dir, pdf_file)
            
            print(f"=== Processing: {pdf_file} ===")
            
            if not os.path.exists(pdf_path):
                print(f"❌ File not found: {pdf_path}")
                continue
                
            try:
                # Get stats before import
                stats_before = self.get_statistics()
                
                # Determine file format based on filename
                if 'round' in pdf_file.lower() or 'result' in pdf_file.lower():
                    file_format = 'all_india'
                else:
                    file_format = 'state'
                
                print(f"Using format: {file_format}")
                
                # Process the PDF file
                total_records = self.process_pdf_file(pdf_path, file_format)
                
                if total_records > 0:
                    print(f"✅ Successfully imported {total_records} records from {pdf_file}")
                    successful_imports += 1
                    total_new_records += total_records
                else:
                    print(f"⚠️ No new records imported from {pdf_file}")
                    
                # Get stats after import
                stats_after = self.get_statistics()
                records_added = stats_after['total_records'] - stats_before['total_records']
                print(f"Database records: {stats_after['total_records']} (net added: {records_added})")
                print()
                    
            except Exception as e:
                print(f"❌ Error importing {pdf_file}: {e}")
                import traceback
                traceback.print_exc()
                print()
        
        # Final statistics
        stats_final = self.get_statistics()
        print(f"=== Final Import Summary ===")
        print(f"Successfully processed: {successful_imports}/{len(pdf_files)} files")
        print(f"Total records imported: {total_new_records}")
        print(f"Initial database records: {stats_initial['total_records']}")
        print(f"Final database records: {stats_final['total_records']}")
        print(f"Net records added: {stats_final['total_records'] - stats_initial['total_records']}")
        print(f"Unique Colleges: {stats_final['unique_colleges']}")
        print(f"Unique Courses: {stats_final['unique_courses']}")
        print(f"By Quota: {stats_final['by_quota']}")
        
        print("\n🎉 Batch import complete!")
        return stats_final
    
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
    
    def process_all_pdfs_in_folder(self, folder_path='pdfs', file_type='state'):
        """Process all PDF files in the specified folder with explicit format
        
        Args:
            folder_path (str): Path to folder containing PDFs
            file_type (str): Format type - 'state' for state quota format, 'all_india' for All India quota format
        """
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
        print(f"Using format: {file_type}")
        
        processing_results = {}
        total_records = 0
        
        for pdf_file in pdf_files:
            try:
                records = self.process_pdf_file(pdf_file, file_type)
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
        elif command == 'status':
            processor.get_detailed_status()
            processor.close()
            sys.exit(0)
        elif command == 'validate':
            processor.validate_state_data()
            processor.close()
            sys.exit(0)
        elif command == 'verify':
            # Show verification status and pending records
            processor.show_verification_status()
            processor.close()
            sys.exit(0)
        elif command == 'batch':
            # Batch import from data/pdfs directory
            if len(sys.argv) > 2:
                pdfs_dir = sys.argv[2]
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                pdfs_dir = os.path.join(base_dir, 'data', 'pdfs')
            
            processor.batch_import_pdfs(pdfs_dir)
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
        elif command == 'import':
            # Import specific file: python pdf_uploader.py import <filepath> <format> [--verify] [--sample-rate=0.1]
            if len(sys.argv) < 4:
                print("Usage: python pdf_uploader.py import <filepath> <format> [--verify] [--sample-rate=0.1]")
                print("Formats: 'state' or 'all_india'")
                print("Options:")
                print("  --verify: Enable verification record creation with sampling")
                print("  --sample-rate=X: Set sampling rate (default 0.1 = 10%)")
                print("Example: python pdf_uploader.py import data/pdfs/DOC-20240822-WA0000.pdf state --verify --sample-rate=0.2")
                processor.close()
                sys.exit(1)
            
            file_path = sys.argv[2]
            file_format = sys.argv[3]
            
            # Parse optional flags
            enable_verification = '--verify' in sys.argv
            sample_rate = 0.1
            for arg in sys.argv[4:]:
                if arg.startswith('--sample-rate='):
                    try:
                        sample_rate = float(arg.split('=')[1])
                        if not 0 < sample_rate <= 1:
                            print("Sample rate must be between 0 and 1")
                            processor.close()
                            sys.exit(1)
                    except ValueError:
                        print("Invalid sample rate format")
                        processor.close()
                        sys.exit(1)
            
            if file_format not in ['state', 'all_india']:
                print("Invalid format. Must be 'state' or 'all_india'")
                processor.close()
                sys.exit(1)
            
            print(f"=== Importing: {os.path.basename(file_path)} ===")
            print(f"Format: {file_format}")
            if enable_verification:
                print(f"Verification: Enabled (sampling rate: {sample_rate*100:.1f}%)")
            
            if os.path.exists(file_path):
                try:
                    # Check current database stats before import
                    stats_before = processor.get_statistics()
                    print(f"Records before import: {stats_before['total_records']}")
                    
                    # Process the PDF file with explicit format and verification
                    total_records = processor.process_pdf_file(
                        file_path, 
                        file_type=file_format,
                        enable_verification=enable_verification,
                        sample_rate=sample_rate
                    )
                    
                    if total_records > 0:
                        print(f"✅ Successfully imported {total_records} records from {os.path.basename(file_path)}")
                    else:
                        print(f"⚠️ No records were imported from {os.path.basename(file_path)}")
                        
                    # Get updated statistics
                    stats_after = processor.get_statistics()
                    print(f"Records after import: {stats_after['total_records']} (net added: {stats_after['total_records'] - stats_before['total_records']})")
                    print(f"Unique Colleges: {stats_after['unique_colleges']}")
                    print(f"Unique Courses: {stats_after['unique_courses']}")
                    print(f"By Quota: {stats_after['by_quota']}")
                        
                except Exception as e:
                    print(f"❌ Error importing {file_path}: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"❌ File not found: {file_path}")
            
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
    print("Using default format: state (for state quota PDFs)")
    processing_results = processor.process_all_pdfs_in_folder('pdfs', 'state')
    
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
    print("  python pdf_uploader.py                    - Process all PDFs (default: state format)")
    print("  python pdf_uploader.py import <file> <format> - Import specific file with format")
    print("  python pdf_uploader.py batch [<dir>]      - Batch import from data/pdfs directory")
    print("  python pdf_uploader.py test               - Test PostgreSQL connection")
    print("  python pdf_uploader.py stats              - Show basic database statistics")
    print("  python pdf_uploader.py status             - Show detailed database status")
    print("  python pdf_uploader.py validate           - Validate state counselling data")
    print("  python pdf_uploader.py verify             - Show verification status and pending records")
    print("  python pdf_uploader.py export             - Export data to JSON")
    print("  python pdf_uploader.py clear              - Clear database (use with caution!)")
    print("\nFormat options:")
    print("  - state: For PDFs with 'State College Name', 'Gender', 'Date of Birth' columns")
    print("  - all_india: For PDFs with 'Round 1 Round 2', 'Counselling Seats Allotment' columns")
    print("\nExamples:")
    print("  python pdf_uploader.py import data/pdfs/DOC-20240822-WA0000.pdf state")
    print("  python pdf_uploader.py import data/pdfs/round_3.pdf all_india")
    print("  python pdf_uploader.py import data/pdfs/DOC-20240822-WA0000.pdf state --verify --sample-rate=0.2")
    print("  python pdf_uploader.py batch                     # Import all PDFs from data/pdfs/")
    print("  python pdf_uploader.py status                    # Detailed analysis with samples")
    print("  python pdf_uploader.py validate                  # Check state data quality")
    print("  python pdf_uploader.py verify                    # Check verification status")
    print("\nDatabase Configuration:")
    print(f"  Host: {processor.db_config['host']}")
    print(f"  Database: {processor.db_config['database']}")
    print(f"  User: {processor.db_config['user']}")
    print(f"  Port: {processor.db_config['port']}")