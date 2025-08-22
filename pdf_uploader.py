import pandas as pd
import sqlite3
import PyPDF2
import pdfplumber
import re
from datetime import datetime
import json

class NEETPGDataProcessor:
    def __init__(self, db_name='neet_pg_counselling.db'):
        """Initialize the processor with database connection"""
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        """Create necessary database tables"""
        
        # Main colleges data table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS counselling_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            file_type TEXT,
            processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            records_count INTEGER
        )
        ''')
        
        self.conn.commit()
    
    def process_state_quota_pdf(self, pdf_path):
        """Process State Quota PDF (like the Andhra Pradesh example)"""
        data_records = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Extract tables if present
                tables = page.extract_tables()
                
                if tables:
                    for table in tables:
                        # Skip header row (index 0)
                        for row in table[1:]:
                            if row and len(row) >= 11:  # Ensure we have enough columns
                                record = self.parse_state_quota_row(row)
                                if record:
                                    data_records.append(record)
                
        return data_records
    
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
        """Process All India Quota PDF"""
        data_records = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
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
                                    data_records.append(record)
                else:
                    # Fallback to text extraction
                    text = page.extract_text()
                    records = self.parse_all_india_text(text)
                    data_records.extend(records)
        
        return data_records
    
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
        """Insert records into database"""
        for record in records:
            try:
                self.cursor.execute('''
                INSERT INTO counselling_data 
                (year, round, rank, quota, state, college_name, course, 
                 category, sub_category, gender, physically_handicapped, 
                 marks_obtained, max_marks, status, date_of_admission)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            except sqlite3.IntegrityError:
                print(f"Duplicate record skipped: Rank {record.get('rank')}")
                continue
        
        self.conn.commit()
    
    def process_pdf_file(self, pdf_path, file_type='auto'):
        """Main method to process any PDF file"""
        print(f"Processing file: {pdf_path}")
        
        # Check if file already processed
        self.cursor.execute('SELECT * FROM processed_files WHERE filename = ?', (pdf_path,))
        if self.cursor.fetchone():
            print(f"File {pdf_path} already processed. Skipping...")
            return
        
        # Determine file type
        if file_type == 'auto':
            with pdfplumber.open(pdf_path) as pdf:
                if pdf.pages:
                    text = pdf.pages[0].extract_text()
                    if ('State College Name' in text or 
                        'State Quota' in text or 
                        'Andhra Pradesh' in text):
                        file_type = 'state'
                    elif ('Round 1 Round 2 Round 3' in text or 
                          'Counselling Seats Allotment' in text or
                          'Allotted Quota' in text):
                        file_type = 'all_india'
                    else:
                        file_type = 'all_india'  # Default fallback
        
        # Process based on type
        if file_type == 'state':
            records = self.process_state_quota_pdf(pdf_path)
        else:
            records = self.process_all_india_pdf(pdf_path)
        
        # Insert records
        if records:
            self.insert_records(records)
            
            # Log processed file
            self.cursor.execute('''
            INSERT INTO processed_files (filename, file_type, records_count)
            VALUES (?, ?, ?)
            ''', (pdf_path, file_type, len(records)))
            self.conn.commit()
            
            print(f"Successfully processed {len(records)} records from {pdf_path}")
        else:
            print(f"No records found in {pdf_path}")
        
        return records
    
    def get_eligible_colleges(self, rank, category=None, quota=None):
        """Get eligible colleges based on rank"""
        query = '''
        SELECT DISTINCT college_name, course, quota, rank as cutoff_rank, 
               category, round, year
        FROM counselling_data
        WHERE rank >= ?
        '''
        params = [rank]
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        if quota:
            query += ' AND quota = ?'
            params.append(quota)
        
        query += ' ORDER BY rank ASC'
        
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
        ORDER BY cutoff_rank ASC
        ''')
        
        data = []
        for row in self.cursor.fetchall():
            data.append({
                'college': row[0],
                'course': row[1],
                'quota': row[2],
                'lastRank': row[3],
                'category': row[4] or 'GENERAL',
                'round': row[5],
                'year': row[6]
            })
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Data exported to {output_file}")
        return data
    
    def close(self):
        """Close database connection"""
        self.conn.close()


# Example usage
if __name__ == "__main__":
    # Initialize processor
    processor = NEETPGDataProcessor()
    
    # Process PDF files
    pdf_files = [
        'state_pg.pdf',
        'pg_round_3.pdf',
    ]
    
    for pdf_file in pdf_files:
        try:
            processor.process_pdf_file(pdf_file)
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
    
    # Get statistics
    stats = processor.get_statistics()
    print("\nDatabase Statistics:")
    print(f"Total Records: {stats['total_records']}")
    print(f"Unique Colleges: {stats['unique_colleges']}")
    print(f"Unique Courses: {stats['unique_courses']}")
    print(f"By Quota: {stats['by_quota']}")
    print(f"By Category: {stats['by_category']}")
    
    # Example: Get eligible colleges for a rank
    rank = 5000
    eligible = processor.get_eligible_colleges(rank)
    print(f"\nColleges eligible for rank {rank}:")
    for college in eligible[:10]:  # Show first 10
        print(f"- {college[0]}: {college[1]} (Cutoff: {college[3]})")
    
    # Export to JSON for web use
    processor.export_to_json()
    
    # Close connection
    processor.close()