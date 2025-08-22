from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

DATABASE = 'neet_pg_counselling.db'

def get_db_connection():
    """Create database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Serve the main HTML page"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>NEET PG College Eligibility API</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            h1 { color: #333; }
            .endpoint { background: #f9f9f9; padding: 15px; margin: 15px 0; border-radius: 5px; }
            code { background: #e9e9e9; padding: 2px 5px; border-radius: 3px; }
            .method { color: #27ae60; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>NEET PG College Eligibility API</h1>
            <p>Welcome to the NEET PG College Eligibility API. Use the following endpoints:</p>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/check-eligibility</code>
                <p>Check eligible colleges based on rank</p>
                <p>Parameters: rank (required), category (optional), quota (optional), limit (optional)</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/colleges</code>
                <p>Get list of all colleges</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/courses</code>
                <p>Get list of all courses</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/statistics</code>
                <p>Get database statistics</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/cutoffs/{college_name}</code>
                <p>Get cutoff ranks for a specific college</p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/api/check-eligibility', methods=['GET'])
def check_eligibility():
    """Check eligible colleges based on rank"""
    try:
        rank = request.args.get('rank', type=int)
        category = request.args.get('category', default=None)
        quota = request.args.get('quota', default=None)
        limit = request.args.get('limit', default=100, type=int)
        
        if not rank:
            return jsonify({'error': 'Rank parameter is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        query = '''
        SELECT DISTINCT 
            college_name,
            course,
            quota,
            MIN(rank) as cutoff_rank,
            category,
            round,
            year,
            state,
            COUNT(*) as seats_filled
        FROM counselling_data
        WHERE rank >= ?
        '''
        params = [rank]
        
        if category and category != 'all':
            query += ' AND (category = ? OR category IS NULL)'
            params.append(category)
        
        if quota and quota != 'all':
            query += ' AND quota = ?'
            params.append(quota)
        
        query += '''
        GROUP BY college_name, course, quota, category
        ORDER BY cutoff_rank ASC
        LIMIT ?
        '''
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Format results
        eligible_colleges = []
        for row in results:
            eligible_colleges.append({
                'college': row['college_name'],
                'course': row['course'],
                'quota': row['quota'],
                'cutoffRank': row['cutoff_rank'],
                'category': row['category'] or 'GENERAL',
                'round': row['round'],
                'year': row['year'],
                'state': row['state'],
                'seatsFilled': row['seats_filled']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'rank': rank,
            'totalEligible': len(eligible_colleges),
            'colleges': eligible_colleges
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/colleges', methods=['GET'])
def get_colleges():
    """Get list of all unique colleges"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT DISTINCT college_name, state, quota
        FROM counselling_data
        WHERE college_name IS NOT NULL
        ORDER BY college_name
        ''')
        
        colleges = []
        for row in cursor.fetchall():
            colleges.append({
                'name': row['college_name'],
                'state': row['state'],
                'quota': row['quota']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'totalColleges': len(colleges),
            'colleges': colleges
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/courses', methods=['GET'])
def get_courses():
    """Get list of all unique courses"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT DISTINCT course, COUNT(*) as college_count
        FROM counselling_data
        WHERE course IS NOT NULL
        GROUP BY course
        ORDER BY college_count DESC
        ''')
        
        courses = []
        for row in cursor.fetchall():
            courses.append({
                'name': row['course'],
                'collegeCount': row['college_count']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'totalCourses': len(courses),
            'courses': courses
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get database statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total records
        cursor.execute('SELECT COUNT(*) as count FROM counselling_data')
        stats['totalRecords'] = cursor.fetchone()['count']
        
        # Records by quota
        cursor.execute('''
        SELECT quota, COUNT(*) as count
        FROM counselling_data
        GROUP BY quota
        ''')
        stats['byQuota'] = {row['quota']: row['count'] for row in cursor.fetchall()}
        
        # Records by category
        cursor.execute('''
        SELECT category, COUNT(*) as count
        FROM counselling_data
        WHERE category IS NOT NULL
        GROUP BY category
        ''')
        stats['byCategory'] = {row['category']: row['count'] for row in cursor.fetchall()}
        
        # Unique colleges
        cursor.execute('SELECT COUNT(DISTINCT college_name) as count FROM counselling_data')
        stats['uniqueColleges'] = cursor.fetchone()['count']
        
        # Unique courses
        cursor.execute('SELECT COUNT(DISTINCT course) as count FROM counselling_data')
        stats['uniqueCourses'] = cursor.fetchone()['count']
        
        # Rank ranges
        cursor.execute('SELECT MIN(rank) as min_rank, MAX(rank) as max_rank FROM counselling_data')
        row = cursor.fetchone()
        stats['rankRange'] = {
            'minimum': row['min_rank'],
            'maximum': row['max_rank']
        }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cutoffs/<college_name>', methods=['GET'])
def get_college_cutoffs(college_name):
    """Get cutoff ranks for a specific college"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT course, category, quota, MIN(rank) as cutoff_rank, round, year
        FROM counselling_data
        WHERE college_name = ?
        GROUP BY course, category, quota, round, year
        ORDER BY cutoff_rank ASC
        ''', (college_name,))
        
        cutoffs = []
        for row in cursor.fetchall():
            cutoffs.append({
                'course': row['course'],
                'category': row['category'] or 'GENERAL',
                'quota': row['quota'],
                'cutoffRank': row['cutoff_rank'],
                'round': row['round'],
                'year': row['year']
            })
        
        conn.close()
        
        if not cutoffs:
            return jsonify({'error': 'College not found'}), 404
        
        return jsonify({
            'success': True,
            'college': college_name,
            'cutoffs': cutoffs
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search():
    """Search for colleges or courses"""
    try:
        query_text = request.args.get('q', '')
        search_type = request.args.get('type', 'all')  # all, college, course
        
        if not query_text:
            return jsonify({'error': 'Search query is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        results = {
            'colleges': [],
            'courses': []
        }
        
        if search_type in ['all', 'college']:
            cursor.execute('''
            SELECT DISTINCT college_name, state, quota
            FROM counselling_data
            WHERE college_name LIKE ?
            LIMIT 20
            ''', (f'%{query_text}%',))
            
            for row in cursor.fetchall():
                results['colleges'].append({
                    'name': row['college_name'],
                    'state': row['state'],
                    'quota': row['quota']
                })
        
        if search_type in ['all', 'course']:
            cursor.execute('''
            SELECT DISTINCT course
            FROM counselling_data
            WHERE course LIKE ?
            LIMIT 20
            ''', (f'%{query_text}%',))
            
            for row in cursor.fetchall():
                results['courses'].append(row['course'])
        
        conn.close()
        
        return jsonify({
            'success': True,
            'query': query_text,
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)