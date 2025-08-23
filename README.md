# NEET PG College Eligibility Checker

A Next.js application for checking college eligibility based on NEET PG ranks.

## Features

- Check eligible colleges based on NEET PG rank, category, and quota
- View college cutoffs for different courses and rounds
- Filter results by specialty type (clinical, non-clinical, surgical)
- Search for specific colleges or courses
- User authentication system
- Responsive design for all devices

## Tech Stack

- **Frontend**: Next.js 14+, TypeScript, Tailwind CSS
- **Backend**: Next.js API Routes
- **Database**: PostgreSQL
- **ORM**: Prisma
- **Authentication**: NextAuth.js
- **Deployment**: Render.com

## Getting Started

### Prerequisites

- Node.js 18.x or higher
- npm or yarn
- PostgreSQL database

### Installation

1. Clone the repository
```bash
git clone https://github.com/your-username/neet-pg-checker.git
cd neet-pg-checker
```

2. Install dependencies
```bash
npm install
```

3. Set up environment variables

Create a `.env` file in the root directory with the following variables:
```
# Database Configuration
DATABASE_URL="postgresql://username:password@localhost:5432/neetpg"
DIRECT_URL="postgresql://username:password@localhost:5432/neetpg"

# NextAuth Configuration
NEXTAUTH_SECRET="your-secret-key-here"
NEXTAUTH_URL="http://localhost:3000"

# Node Environment
NODE_ENV="development"
```

4. Generate Prisma client
```bash
npm run prisma:generate
```

5. Run database migrations
```bash
npx prisma migrate dev
```

6. Seed the database (if you have existing counselling_data.json)
```bash
npm run prisma:seed
```

7. Start the development server
```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

## Database Migration

If you're migrating from the previous Flask application:

1. Export data from the old PostgreSQL database:
```bash
# In your Flask application directory
python pdf_uploader.py export
```

2. Copy the `counselling_data.json` file to the root of this project.

3. Run the seed script to import the data:
```bash
npm run prisma:seed
```

## Deployment

This project is configured for deployment on [Render.com](https://render.com).

### Deploying to Render

1. Push your code to GitHub
2. On Render, create a new Blueprint
3. Connect to your GitHub repository
4. Render will automatically use the `render.yaml` configuration to set up:
   - Web service for the Next.js application
   - PostgreSQL database

### Environment Variables

Make sure to set the following environment variables on Render:

- `DATABASE_URL`: PostgreSQL connection string (provided by Render)
- `DIRECT_URL`: Direct connection string for PostgreSQL (provided by Render)
- `NEXTAUTH_SECRET`: Secret key for NextAuth.js
- `NEXTAUTH_URL`: Your application URL (e.g., https://your-app.onrender.com)
- `NODE_ENV`: Set to `production`

## API Documentation

### Authentication Endpoints

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/[...nextauth]` - NextAuth.js endpoints for authentication

### Data Endpoints

- `GET /api/eligibility` - Get eligible colleges based on rank
- `GET /api/colleges` - Get list of all colleges
- `GET /api/courses` - Get list of all courses
- `GET /api/cutoffs/{collegeName}` - Get cutoff ranks for a specific college
- `GET /api/search` - Search for colleges or courses
- `GET /api/statistics` - Get database statistics
- `GET /api/health` - Health check endpoint

## License

This project is licensed under the MIT License.