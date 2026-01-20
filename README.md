# Wallet Agent - Expense Tracker

A manual expense tracking app with clean UX, recurring expense reminders, and data visualization.

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Recharts
- **Backend**: FastAPI, Python 3.11+, SQLAlchemy 2.0
- **Database**: PostgreSQL 16 (Docker)

## Quick Start

### 1. Start PostgreSQL Database

```bash
docker-compose up -d
```

### 2. Setup Backend

```bash
cd backend

# Install uv (if not already installed)
# Windows:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux/Mac:
# curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies (creates .venv automatically)
uv sync

# Run migrations
uv run alembic upgrade head

# Start the server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

### 3. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:3000`

## Features

- ✅ Dashboard with spending charts (pie & bar charts)
- ✅ Quick-add buttons for frequent categories
- ✅ Expense CRUD with filtering & pagination
- ✅ Category management
- ✅ Recurring expense reminders
- ✅ CSV export

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/categories | List all categories |
| POST | /api/v1/categories | Create category |
| GET | /api/v1/expenses | List expenses (paginated) |
| POST | /api/v1/expenses | Create expense |
| PUT | /api/v1/expenses/{id} | Update expense |
| DELETE | /api/v1/expenses/{id} | Delete expense |
| GET | /api/v1/recurring | List recurring expenses |
| POST | /api/v1/recurring | Create recurring expense |
| PUT | /api/v1/recurring/{id} | Update recurring expense |
| DELETE | /api/v1/recurring/{id} | Delete recurring expense |
| GET | /api/v1/stats/summary | Get spending summary |
| GET | /api/v1/stats/upcoming-recurring | Get upcoming reminders |
| GET | /api/v1/export/csv | Export expenses as CSV |

## Project Structure

```
expense-tracker/
├── docker-compose.yml
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── alembic/
│   │   └── versions/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models/
│       ├── schemas/
│       └── routers/
└── frontend/
    ├── package.json
    └── src/
        ├── app/
        ├── components/
        ├── hooks/
        ├── lib/
        └── types/
```
