-- NEET PG Counselling Database Schema for PostgreSQL
-- Main counselling data table
CREATE TABLE IF NOT EXISTS counselling_data (
    id SERIAL PRIMARY KEY,
    year INTEGER,
    round INTEGER,
    rank INTEGER,
    quota VARCHAR(50),
    state VARCHAR(100),
    college_name TEXT,
    course TEXT,
    category VARCHAR(20),
    sub_category VARCHAR(50),
    gender VARCHAR(10),
    physically_handicapped VARCHAR(10),
    marks_obtained INTEGER,
    max_marks INTEGER,
    status VARCHAR(100),
    date_of_admission VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for tracking processed files
CREATE TABLE IF NOT EXISTS processed_files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE,
    file_type VARCHAR(20),
    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    records_count INTEGER
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_rank ON counselling_data(rank);
CREATE INDEX IF NOT EXISTS idx_quota ON counselling_data(quota);
CREATE INDEX IF NOT EXISTS idx_category ON counselling_data(category);
CREATE INDEX IF NOT EXISTS idx_college ON counselling_data USING HASH(college_name);
CREATE INDEX IF NOT EXISTS idx_course ON counselling_data USING HASH(course);
CREATE INDEX IF NOT EXISTS idx_year_round ON counselling_data(year, round);
CREATE INDEX IF NOT EXISTS idx_state ON counselling_data(state);

-- Add comments for documentation
COMMENT ON TABLE counselling_data IS 'NEET PG counselling allocation data from State and All India quota';
COMMENT ON TABLE processed_files IS 'Tracks processed PDF files to avoid duplicates';

-- Display table info (PostgreSQL equivalent)
\d counselling_data;
\d processed_files;