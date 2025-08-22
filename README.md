# NEET PG College Eligibility Checker

A comprehensive web application to check college eligibility based on NEET PG ranks and counselling data. Built with Flask and PostgreSQL, optimized for deployment on Render.com.

## Features

- ✅ Check eligible colleges based on NEET PG rank
- 🔍 Filter by category (General, OBC, SC, ST, EWS)
- 🏥 Filter by quota (All India, State Quota, Delhi University)
- 🔎 Search for specific colleges and courses
- 📊 View college-wise cutoff ranks and statistics
- 📱 Responsive web interface with modern UI
- 🚀 RESTful API with comprehensive endpoints
- 🐘 PostgreSQL database for reliability and performance

## Architecture

- **Backend**: Flask (Python)
- **Database**: PostgreSQL
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Deployment**: Render.com
- **API**: RESTful with JSON responses

## Quick Start

### Local Development

1. **Clone and Setup**:
```bash
git clone <repository-url>
cd neet-pg-checker
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Setup PostgreSQL Database**:
```bash
# Make sure PostgreSQL is running
# Create database 'neetpg' with user 'avesh'
psql -U postgres -c "CREATE DATABASE neetpg;"
psql -U postgres -c "CREATE USER avesh WITH PASSWORD 'your_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE neetpg TO avesh;"
```

3. **Initialize Database**:
```bash
python init_db.py
```

4. **Run Application**:
```bash
python app.py
```

The application will be available at `http://localhost:8001`

### Production Deployment (Render.com)

1. **Push to GitHub**: Ensure your code is in a GitHub repository

2. **Create Services on Render.com**:
   - **Database**: Create a PostgreSQL database service
   - **Web Service**: Create a web service connected to your repository

3. **Configure Web Service**:
   - **Build Command**: `pip install -r requirements.txt && python init_db.py`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - **Environment Variables**: DATABASE_URL (auto-provided by Render)

4. **Deploy**: Render will automatically deploy your application

## API Documentation

### Base URL
- Local: `http://localhost:8001`
- Production: `https://your-app-name.onrender.com`

### Endpoints

#### Health Check
```http
GET /health
```
Returns application health status and database connectivity.

#### Database Statistics
```http
GET /api/statistics
```
Returns comprehensive database statistics including record counts, unique colleges/courses, and rank ranges.

#### Eligibility Check
```http
GET /api/check-eligibility?rank=5000&category=GENERAL&quota=AI&limit=50
```
**Parameters**:
- `rank` (required): NEET PG rank (integer)
- `category` (optional): `GENERAL`, `OBC`, `SC`, `ST`, `EWS`, or `all` (default: `all`)
- `quota` (optional): `AI`, `DU`, `State Quota`, or `all` (default: `all`)
- `limit` (optional): Number of results (default: 100, max: 500)

#### College Information
```http
GET /api/colleges
GET /api/cutoffs/<college_name>
```

#### Course Information
```http
GET /api/courses
```

#### Search
```http
GET /api/search?q=medical&type=college
```
**Parameters**:
- `q` (required): Search query
- `type` (optional): `college`, `course`, or `all` (default: `all`)

## Database Schema

### counselling_data Table
```sql
CREATE TABLE counselling_data (
    id SERIAL PRIMARY KEY,
    year INTEGER,
    round INTEGER,
    rank INTEGER,
    quota TEXT,
    state TEXT,
    college_name TEXT,
    course TEXT,
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Sample Data Format
```json
{
  "year": 2024,
  "round": 1,
  "rank": 5000,
  "quota": "AI",
  "state": "Delhi",
  "college_name": "AIIMS New Delhi",
  "course": "MD - General Medicine",
  "category": "GENERAL"
}
```

## Development

### Project Structure
```
neet-pg-checker/
├── app.py                 # Main Flask application
├── init_db.py            # Database initialization script
├── web.html              # Frontend interface
├── requirements.txt      # Python dependencies
├── render.yaml          # Render.com configuration
├── Procfile             # Alternative deployment config
├── runtime.txt          # Python version specification
└── README.md           # This file
```

### Key Features Implementation

1. **Database Connection**: Automatic detection of local vs production environment
2. **Query Optimization**: Indexed database fields for fast searches
3. **Error Handling**: Comprehensive error handling with meaningful messages
4. **CORS Support**: Enabled for cross-origin requests
5. **Health Monitoring**: Built-in health check endpoint for monitoring
6. **Responsive Design**: Mobile-friendly interface

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (auto-provided by Render)
- `PORT`: Application port (auto-provided by Render, defaults to 8001 locally)

## Performance Considerations

- **Database Indexing**: Optimized indexes on frequently queried columns
- **Connection Pooling**: Efficient database connection management
- **Query Optimization**: Optimized SQL queries for fast response times
- **Caching**: Browser-side caching for static assets

## Security Features

- **SQL Injection Protection**: Parameterized queries
- **CORS Configuration**: Proper cross-origin resource sharing setup
- **Error Handling**: Secure error messages without sensitive information exposure

## Monitoring and Debugging

- Health check endpoint at `/health`
- Detailed error logging
- Database connection status monitoring
- Performance metrics available through API

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - feel free to use this project for educational or commercial purposes.

## Support

For issues or questions:
1. Check the API endpoints using the health check
2. Verify database connectivity
3. Review application logs
4. Create an issue on GitHub

---

**Note**: This application is optimized for Render.com deployment but can be deployed on any platform that supports Python and PostgreSQL.