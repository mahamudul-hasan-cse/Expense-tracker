# Wallet Agent - Technical Specification

> A manual expense tracker with clean UX, recurring expense reminders, and data visualization.
> Built with Next.js, FastAPI, PostgreSQL (Docker).

---

## 1. Project Overview

**Product Name:** Wallet Agent

**Purpose:** Simple expense tracking app where users manually log expenses via form + quick-add buttons, view spending history, visualize data with charts, manage recurring expenses, and export data.

**No AI/LLM components** — purely manual input with good UX.

---

## 2. Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14+ (App Router), TypeScript, Tailwind CSS |
| UI Components | shadcn/ui |
| Charts | Recharts |
| Backend | FastAPI (Python 3.11+) |
| Database | PostgreSQL 16 (Docker) |
| ORM | SQLAlchemy 2.0 |
| API Communication | REST (JSON) |
| State Management | React hooks + Context (no Redux needed) |

---

## 3. Database Schema

### 3.1 Docker Setup

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:16-alpine
    container_name: wallet_agent_db
    environment:
      POSTGRES_USER: wallet_user
      POSTGRES_PASSWORD: wallet_pass
      POSTGRES_DB: wallet_agent
    ports:
      - "5432:5432"
    volumes:
      - wallet_data:/var/lib/postgresql/data

volumes:
  wallet_data:
```

### 3.2 Tables

#### `categories` table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| name | VARCHAR(100) | NOT NULL, UNIQUE | Category name |
| icon | VARCHAR(50) | NULLABLE | Optional emoji or icon name |
| is_default | BOOLEAN | DEFAULT false | System default category |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation timestamp |

**Default seed data:**
```sql
INSERT INTO categories (name, icon, is_default) VALUES
  ('Rickshaw', '🛺', true),
  ('Wifi Bill', '📶', true),
  ('Random', '🎲', true),
  ('Smoking', '🚬', true);
```

#### `expenses` table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| amount | DECIMAL(12,2) | NOT NULL, CHECK (amount > 0) | Amount in Taka |
| category_id | UUID | FOREIGN KEY → categories(id) | Category reference |
| note | VARCHAR(500) | NULLABLE | Optional description/merchant |
| expense_date | DATE | NOT NULL, DEFAULT CURRENT_DATE | Date of expense |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update time |

**Indexes:**
```sql
CREATE INDEX idx_expenses_date ON expenses(expense_date DESC);
CREATE INDEX idx_expenses_category ON expenses(category_id);
CREATE INDEX idx_expenses_date_category ON expenses(expense_date, category_id);
```

#### `recurring_expenses` table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| name | VARCHAR(200) | NOT NULL | Expense name (e.g., "Monthly Wifi") |
| amount | DECIMAL(12,2) | NOT NULL, CHECK (amount > 0) | Amount in Taka |
| category_id | UUID | FOREIGN KEY → categories(id) | Category reference |
| frequency | VARCHAR(20) | NOT NULL, CHECK IN ('weekly', 'monthly') | Recurrence type |
| due_day | INTEGER | NOT NULL, CHECK (1-31 for monthly, 1-7 for weekly) | Day of week (1=Mon) or day of month |
| is_active | BOOLEAN | DEFAULT true | Active status |
| last_reminded_at | DATE | NULLABLE | Last reminder shown |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation timestamp |

---

## 4. API Endpoints (FastAPI)

Base URL: `http://localhost:8000/api/v1`

### 4.1 Categories

#### GET `/categories`
Returns all categories.

**Response:**
```json
{
  "categories": [
    {
      "id": "uuid",
      "name": "Rickshaw",
      "icon": "🛺",
      "is_default": true
    }
  ]
}
```

#### POST `/categories`
Create new category.

**Request:**
```json
{
  "name": "Gym",
  "icon": "💪"
}
```

**Response:** `201 Created` with category object.

**Validation:**
- `name`: required, 1-100 chars, unique (case-insensitive)
- `icon`: optional, max 50 chars

---

### 4.2 Expenses

#### GET `/expenses`
List expenses with filtering and pagination.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | int | 1 | Page number |
| limit | int | 50 | Items per page (max 100) |
| category_id | UUID | null | Filter by category |
| start_date | date | null | Filter from date (inclusive) |
| end_date | date | null | Filter to date (inclusive) |
| sort | string | "date_desc" | Sort: date_desc, date_asc, amount_desc, amount_asc |

**Response:**
```json
{
  "expenses": [
    {
      "id": "uuid",
      "amount": 350.00,
      "category": {
        "id": "uuid",
        "name": "Food",
        "icon": "🍔"
      },
      "note": "Lunch at Chillox",
      "expense_date": "2026-01-17",
      "created_at": "2026-01-17T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total_items": 234,
    "total_pages": 5
  }
}
```

#### POST `/expenses`
Create new expense.

**Request:**
```json
{
  "amount": 350.00,
  "category_id": "uuid",
  "note": "Lunch at Chillox",
  "expense_date": "2026-01-17"
}
```

**Validation:**
- `amount`: required, positive number, max 2 decimal places
- `category_id`: required, must exist
- `note`: optional, max 500 chars
- `expense_date`: optional (defaults to today), cannot be future date

**Response:** `201 Created` with expense object.

#### PUT `/expenses/{id}`
Update existing expense.

**Request:** Same as POST (all fields optional except at least one must be provided).

**Response:** `200 OK` with updated expense object.

#### DELETE `/expenses/{id}`
Delete expense.

**Response:** `204 No Content`

---

### 4.3 Recurring Expenses

#### GET `/recurring`
List all recurring expenses.

**Response:**
```json
{
  "recurring_expenses": [
    {
      "id": "uuid",
      "name": "Monthly Wifi",
      "amount": 800.00,
      "category": {
        "id": "uuid",
        "name": "Wifi Bill",
        "icon": "📶"
      },
      "frequency": "monthly",
      "due_day": 5,
      "is_active": true,
      "next_due": "2026-02-05"
    }
  ]
}
```

**Note:** `next_due` is calculated server-side based on frequency and due_day.

#### POST `/recurring`
Create recurring expense.

**Request:**
```json
{
  "name": "Monthly Wifi",
  "amount": 800.00,
  "category_id": "uuid",
  "frequency": "monthly",
  "due_day": 5
}
```

**Validation:**
- `name`: required, 1-200 chars
- `amount`: required, positive number
- `category_id`: required, must exist
- `frequency`: required, "weekly" or "monthly"
- `due_day`: required, 1-7 for weekly (1=Monday), 1-31 for monthly

#### PUT `/recurring/{id}`
Update recurring expense.

#### DELETE `/recurring/{id}`
Delete recurring expense.

---

### 4.4 Dashboard / Statistics

#### GET `/stats/summary`
Get spending summary.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| period | string | "monthly" | "weekly" or "monthly" |
| date | date | today | Reference date for the period |

**Response:**
```json
{
  "period": "monthly",
  "start_date": "2026-01-01",
  "end_date": "2026-01-31",
  "total_spent": 15420.00,
  "by_category": [
    {
      "category_id": "uuid",
      "category_name": "Food",
      "category_icon": "🍔",
      "total": 5200.00,
      "percentage": 33.7,
      "count": 24
    }
  ],
  "daily_totals": [
    { "date": "2026-01-01", "total": 450.00 },
    { "date": "2026-01-02", "total": 800.00 }
  ]
}
```

#### GET `/stats/upcoming-recurring`
Get upcoming recurring expense reminders.

**Response:**
```json
{
  "upcoming": [
    {
      "id": "uuid",
      "name": "Monthly Wifi",
      "amount": 800.00,
      "due_date": "2026-01-20",
      "days_until": 3,
      "category": { "name": "Wifi Bill", "icon": "📶" }
    }
  ]
}
```

**Logic:** Return recurring expenses due within next 7 days.

---

### 4.5 Export

#### GET `/export/csv`
Export expenses as CSV.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| start_date | date | From date (required) |
| end_date | date | To date (required) |

**Response:** CSV file download.

**CSV Columns:**
```
Date,Amount,Category,Note
2026-01-17,350.00,Food,Lunch at Chillox
```

---

## 5. Frontend Pages & Components

### 5.1 Page Structure

```
/                     → Dashboard (default view)
/expenses             → Expense list with filters
/settings             → Categories, recurring expenses, export
```

### 5.2 Dashboard Page (`/`)

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  [Weekly | Monthly] toggle              Total: ৳15,420  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────┐  ┌─────────────────────────┐  │
│  │                     │  │  Upcoming Reminders     │  │
│  │   PIE CHART         │  │  ┌───────────────────┐  │  │
│  │   (by category)     │  │  │ 📶 Wifi - 3 days  │  │  │
│  │                     │  │  │ ৳800              │  │  │
│  └─────────────────────┘  │  └───────────────────┘  │  │
│                           └─────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              BAR CHART (daily totals)           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  QUICK ADD BUTTONS                                      │
│  [🛺 Rickshaw] [📶 Wifi] [🎲 Random] [🚬 Smoking] [+]  │
├─────────────────────────────────────────────────────────┤
│  RECENT EXPENSES (last 5)                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Today · ৳350 · 🍔 Food · Lunch at Chillox  [✎] │   │
│  │ Today · ৳30 · 🛺 Rickshaw · Campus         [✎] │   │
│  └─────────────────────────────────────────────────┘   │
│                                      [View All →]       │
└─────────────────────────────────────────────────────────┘
```

**Components:**
1. **Period Toggle** — Switch between weekly/monthly view
2. **Summary Card** — Total spent for period
3. **Pie Chart** — Category breakdown (Recharts)
4. **Bar Chart** — Daily spending (Recharts)
5. **Upcoming Reminders** — Recurring expenses due within 7 days
6. **Quick Add Buttons** — One-tap logging for frequent categories
7. **Recent Expenses List** — Last 5 expenses with edit button

---

### 5.3 Expense List Page (`/expenses`)

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  Expenses                              [+ Add Expense]  │
├─────────────────────────────────────────────────────────┤
│  FILTERS                                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │ Category ▼   │ │ From Date    │ │ To Date      │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
│                                          [Clear Filters]│
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐   │
│  │ DATE        AMOUNT    CATEGORY    NOTE     ACT  │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ Jan 17      ৳350      🍔 Food     Chillox  [✎]🗑│   │
│  │ Jan 17      ৳30       🛺 Rickshaw Campus   [✎]🗑│   │
│  │ Jan 16      ৳800      📶 Wifi     Monthly  [✎]🗑│   │
│  │ ...                                             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [← Prev]  Page 1 of 5  [Next →]                       │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- Filterable by category (dropdown) and date range (date pickers)
- Inline edit via modal/sheet
- Delete with confirmation dialog
- Pagination

---

### 5.4 Settings Page (`/settings`)

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  Settings                                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  CATEGORIES                                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 🛺 Rickshaw (default)                           │   │
│  │ 📶 Wifi Bill (default)                          │   │
│  │ 🎲 Random (default)                             │   │
│  │ 🚬 Smoking (default)                            │   │
│  │ 💪 Gym                               [✎] [🗑]   │   │
│  └─────────────────────────────────────────────────┘   │
│                                   [+ Add Category]      │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  RECURRING EXPENSES                                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │ NAME          AMOUNT   FREQ     DUE    STATUS   │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ Monthly Wifi  ৳800     Monthly  5th    ✓ Active │   │
│  │ Gym Fee       ৳1500    Monthly  1st    ✓ Active │   │
│  └─────────────────────────────────────────────────┘   │
│                              [+ Add Recurring Expense]  │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  EXPORT DATA                                            │
│  ┌──────────────┐ ┌──────────────┐                     │
│  │ From Date    │ │ To Date      │  [Download CSV]     │
│  └──────────────┘ └──────────────┘                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### 5.5 Modals / Sheets

#### Add/Edit Expense Modal

```
┌─────────────────────────────────────┐
│  Add Expense                    [×] │
├─────────────────────────────────────┤
│                                     │
│  Amount (৳) *                       │
│  ┌─────────────────────────────┐   │
│  │ 350                         │   │
│  └─────────────────────────────┘   │
│                                     │
│  Category *                         │
│  ┌─────────────────────────────┐   │
│  │ Food                      ▼ │   │
│  ├─────────────────────────────┤   │
│  │ 🛺 Rickshaw                 │   │
│  │ 📶 Wifi Bill                │   │
│  │ 🍔 Food                     │   │
│  │ ──────────────────────────  │   │
│  │ + Add new category...       │   │
│  └─────────────────────────────┘   │
│                                     │
│  Note (optional)                    │
│  ┌─────────────────────────────┐   │
│  │ Lunch at Chillox            │   │
│  └─────────────────────────────┘   │
│                                     │
│  Date                               │
│  ┌─────────────────────────────┐   │
│  │ 📅 January 17, 2026         │   │
│  └─────────────────────────────┘   │
│                                     │
│           [Cancel]  [Save Expense]  │
└─────────────────────────────────────┘
```

#### Quick Add Modal (from quick buttons)

```
┌─────────────────────────────────────┐
│  🛺 Rickshaw                    [×] │
├─────────────────────────────────────┤
│                                     │
│  Amount (৳) *                       │
│  ┌─────────────────────────────┐   │
│  │                             │   │
│  └─────────────────────────────┘   │
│                                     │
│  Note (optional)                    │
│  ┌─────────────────────────────┐   │
│  │                             │   │
│  └─────────────────────────────┘   │
│                                     │
│                        [Save ৳___]  │
└─────────────────────────────────────┘
```

*Category pre-selected, date defaults to today, minimal fields.*

#### Add Recurring Expense Modal

```
┌─────────────────────────────────────┐
│  Add Recurring Expense          [×] │
├─────────────────────────────────────┤
│                                     │
│  Name *                             │
│  ┌─────────────────────────────┐   │
│  │ Monthly Wifi                │   │
│  └─────────────────────────────┘   │
│                                     │
│  Amount (৳) *                       │
│  ┌─────────────────────────────┐   │
│  │ 800                         │   │
│  └─────────────────────────────┘   │
│                                     │
│  Category *                         │
│  ┌─────────────────────────────┐   │
│  │ 📶 Wifi Bill              ▼ │   │
│  └─────────────────────────────┘   │
│                                     │
│  Frequency *                        │
│  ┌─────────────────────────────┐   │
│  │ Monthly                   ▼ │   │
│  └─────────────────────────────┘   │
│                                     │
│  Due Day *                          │
│  ┌─────────────────────────────┐   │
│  │ 5                         ▼ │   │
│  └─────────────────────────────┘   │
│  (Day of month: 1-31)               │
│                                     │
│              [Cancel]  [Save]       │
└─────────────────────────────────────┘
```

---

## 6. shadcn/ui Components to Use

```bash
# Install these components
npx shadcn@latest add button
npx shadcn@latest add input
npx shadcn@latest add select
npx shadcn@latest add dialog
npx shadcn@latest add sheet
npx shadcn@latest add card
npx shadcn@latest add table
npx shadcn@latest add calendar
npx shadcn@latest add popover
npx shadcn@latest add dropdown-menu
npx shadcn@latest add alert-dialog
npx shadcn@latest add toast
npx shadcn@latest add tabs
npx shadcn@latest add badge
npx shadcn@latest add separator
```

**Component Mapping:**

| UI Element | shadcn Component |
|------------|------------------|
| Period toggle (Weekly/Monthly) | `Tabs` |
| Add expense button | `Button` |
| Expense form inputs | `Input`, `Select`, `Calendar` + `Popover` |
| Category dropdown with "add new" | `Select` with custom footer |
| Expense list | `Table` |
| Edit/Delete actions | `DropdownMenu` or inline `Button` |
| Add/Edit modals | `Dialog` or `Sheet` |
| Delete confirmation | `AlertDialog` |
| Success/Error messages | `Toast` (via `sonner`) |
| Summary cards | `Card` |
| Filter section | `Card` with `Select`, `Popover` + `Calendar` |

---

## 7. Project Structure

```
wallet-agent/
├── docker-compose.yml
│
├── backend/
│   ├── requirements.txt
│   ├── alembic/                    # DB migrations
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── config.py               # Environment config
│   │   ├── database.py             # DB connection
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── category.py
│   │   │   ├── expense.py
│   │   │   └── recurring.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── category.py         # Pydantic schemas
│   │   │   ├── expense.py
│   │   │   └── recurring.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── categories.py
│   │   │   ├── expenses.py
│   │   │   ├── recurring.py
│   │   │   ├── stats.py
│   │   │   └── export.py
│   │   └── services/
│   │       ├── __init__.py
│   │       └── stats.py            # Business logic
│   └── tests/
│
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── components.json             # shadcn config
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # Dashboard
│   │   │   ├── expenses/
│   │   │   │   └── page.tsx
│   │   │   └── settings/
│   │   │       └── page.tsx
│   │   ├── components/
│   │   │   ├── ui/                 # shadcn components
│   │   │   ├── dashboard/
│   │   │   │   ├── period-toggle.tsx
│   │   │   │   ├── summary-card.tsx
│   │   │   │   ├── category-pie-chart.tsx
│   │   │   │   ├── daily-bar-chart.tsx
│   │   │   │   ├── upcoming-reminders.tsx
│   │   │   │   ├── quick-add-buttons.tsx
│   │   │   │   └── recent-expenses.tsx
│   │   │   ├── expenses/
│   │   │   │   ├── expense-table.tsx
│   │   │   │   ├── expense-filters.tsx
│   │   │   │   ├── expense-form.tsx
│   │   │   │   └── delete-dialog.tsx
│   │   │   ├── settings/
│   │   │   │   ├── category-list.tsx
│   │   │   │   ├── category-form.tsx
│   │   │   │   ├── recurring-list.tsx
│   │   │   │   ├── recurring-form.tsx
│   │   │   │   └── export-section.tsx
│   │   │   └── shared/
│   │   │       ├── navbar.tsx
│   │   │       ├── page-header.tsx
│   │   │       └── loading-spinner.tsx
│   │   ├── hooks/
│   │   │   ├── use-expenses.ts
│   │   │   ├── use-categories.ts
│   │   │   ├── use-recurring.ts
│   │   │   └── use-stats.ts
│   │   ├── lib/
│   │   │   ├── api.ts              # API client (fetch wrapper)
│   │   │   ├── utils.ts
│   │   │   └── constants.ts
│   │   └── types/
│   │       └── index.ts            # TypeScript interfaces
│   └── .env.local
│
└── README.md
```

---

## 8. TypeScript Interfaces (Frontend)

```typescript
// src/types/index.ts

export interface Category {
  id: string;
  name: string;
  icon: string | null;
  is_default: boolean;
}

export interface Expense {
  id: string;
  amount: number;
  category: Category;
  note: string | null;
  expense_date: string; // "YYYY-MM-DD"
  created_at: string;
}

export interface ExpenseCreate {
  amount: number;
  category_id: string;
  note?: string;
  expense_date?: string;
}

export interface ExpenseUpdate {
  amount?: number;
  category_id?: string;
  note?: string;
  expense_date?: string;
}

export interface RecurringExpense {
  id: string;
  name: string;
  amount: number;
  category: Category;
  frequency: "weekly" | "monthly";
  due_day: number;
  is_active: boolean;
  next_due: string; // Calculated by backend
}

export interface RecurringExpenseCreate {
  name: string;
  amount: number;
  category_id: string;
  frequency: "weekly" | "monthly";
  due_day: number;
}

export interface CategoryBreakdown {
  category_id: string;
  category_name: string;
  category_icon: string | null;
  total: number;
  percentage: number;
  count: number;
}

export interface DailyTotal {
  date: string;
  total: number;
}

export interface StatsSummary {
  period: "weekly" | "monthly";
  start_date: string;
  end_date: string;
  total_spent: number;
  by_category: CategoryBreakdown[];
  daily_totals: DailyTotal[];
}

export interface UpcomingReminder {
  id: string;
  name: string;
  amount: number;
  due_date: string;
  days_until: number;
  category: Pick<Category, "name" | "icon">;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total_items: number;
    total_pages: number;
  };
}
```

---

## 9. API Client (Frontend)

```typescript
// src/lib/api.ts

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function request<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "API request failed");
  }

  // Handle 204 No Content
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export const api = {
  // Categories
  getCategories: () => request<{ categories: Category[] }>("/categories"),
  createCategory: (data: { name: string; icon?: string }) =>
    request<Category>("/categories", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Expenses
  getExpenses: (params?: {
    page?: number;
    limit?: number;
    category_id?: string;
    start_date?: string;
    end_date?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) searchParams.set(key, String(value));
      });
    }
    return request<PaginatedResponse<Expense>>(
      `/expenses?${searchParams.toString()}`
    );
  },
  createExpense: (data: ExpenseCreate) =>
    request<Expense>("/expenses", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateExpense: (id: string, data: ExpenseUpdate) =>
    request<Expense>(`/expenses/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteExpense: (id: string) =>
    request<void>(`/expenses/${id}`, { method: "DELETE" }),

  // Recurring
  getRecurring: () =>
    request<{ recurring_expenses: RecurringExpense[] }>("/recurring"),
  createRecurring: (data: RecurringExpenseCreate) =>
    request<RecurringExpense>("/recurring", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateRecurring: (id: string, data: Partial<RecurringExpenseCreate>) =>
    request<RecurringExpense>(`/recurring/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteRecurring: (id: string) =>
    request<void>(`/recurring/${id}`, { method: "DELETE" }),

  // Stats
  getStats: (period: "weekly" | "monthly", date?: string) => {
    const params = new URLSearchParams({ period });
    if (date) params.set("date", date);
    return request<StatsSummary>(`/stats/summary?${params.toString()}`);
  },
  getUpcoming: () =>
    request<{ upcoming: UpcomingReminder[] }>("/stats/upcoming-recurring"),

  // Export
  exportCSV: (start_date: string, end_date: string) => {
    window.open(
      `${API_BASE}/export/csv?start_date=${start_date}&end_date=${end_date}`,
      "_blank"
    );
  },
};
```

---

## 10. Implementation Order (Step-by-Step)

### Phase 1: Setup & Database

```
Step 1.1: Create project folders (backend/, frontend/)
Step 1.2: Create docker-compose.yml for PostgreSQL
Step 1.3: Setup FastAPI project with requirements.txt
Step 1.4: Configure SQLAlchemy + Alembic
Step 1.5: Create database models (Category, Expense, RecurringExpense)
Step 1.6: Create initial migration
Step 1.7: Add seed data for default categories
Step 1.8: Test database connection
```

### Phase 2: Backend API

```
Step 2.1: Create Pydantic schemas for all models
Step 2.2: Implement /categories endpoints (GET, POST)
Step 2.3: Implement /expenses endpoints (GET, POST, PUT, DELETE)
Step 2.4: Add filtering & pagination to GET /expenses
Step 2.5: Implement /recurring endpoints (GET, POST, PUT, DELETE)
Step 2.6: Implement /stats/summary endpoint
Step 2.7: Implement /stats/upcoming-recurring endpoint
Step 2.8: Implement /export/csv endpoint
Step 2.9: Add CORS middleware for frontend
Step 2.10: Test all endpoints with curl/Postman
```

### Phase 3: Frontend Setup

```
Step 3.1: Create Next.js project with TypeScript
Step 3.2: Install & configure Tailwind CSS
Step 3.3: Install & configure shadcn/ui
Step 3.4: Install Recharts
Step 3.5: Create TypeScript interfaces
Step 3.6: Create API client (lib/api.ts)
Step 3.7: Create basic layout with navbar
```

### Phase 4: Core Features

```
Step 4.1: Build expense form component (add/edit)
Step 4.2: Build expense table component
Step 4.3: Build expense filters component
Step 4.4: Build /expenses page (list view)
Step 4.5: Add delete confirmation dialog
Step 4.6: Add toast notifications
```

### Phase 5: Dashboard

```
Step 5.1: Build period toggle (weekly/monthly)
Step 5.2: Build summary card
Step 5.3: Build category pie chart
Step 5.4: Build daily bar chart
Step 5.5: Build upcoming reminders component
Step 5.6: Build quick-add buttons
Step 5.7: Build recent expenses list
Step 5.8: Assemble dashboard page
```

### Phase 6: Settings

```
Step 6.1: Build category list component
Step 6.2: Build category form (add/edit)
Step 6.3: Build recurring expense list
Step 6.4: Build recurring expense form
Step 6.5: Build export section
Step 6.6: Assemble settings page
```

### Phase 7: Polish

```
Step 7.1: Add loading states
Step 7.2: Add error handling
Step 7.3: Add empty states
Step 7.4: Mobile responsive testing
Step 7.5: Final testing & bug fixes
```

---

## 11. Environment Variables

### Backend (.env)

```env
DATABASE_URL=postgresql://wallet_user:wallet_pass@localhost:5432/wallet_agent
CORS_ORIGINS=http://localhost:3000
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 12. Key Validation Rules

| Field | Rules |
|-------|-------|
| Amount | Required, > 0, max 2 decimals, max value 99999999.99 |
| Category name | Required, 1-100 chars, unique (case-insensitive) |
| Expense note | Optional, max 500 chars |
| Expense date | Cannot be future date |
| Recurring name | Required, 1-200 chars |
| Recurring due_day | 1-7 for weekly, 1-31 for monthly |

---

## 13. Currency Formatting

Always display Taka with the symbol: `৳`

```typescript
// src/lib/utils.ts
export function formatCurrency(amount: number): string {
  return `৳${amount.toLocaleString("en-BD", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
}
```

---

## 14. Date Formatting

Use consistent date formats:

| Context | Format | Example |
|---------|--------|---------|
| Display in list | "MMM D" | "Jan 17" |
| Display with year | "MMM D, YYYY" | "Jan 17, 2026" |
| API request | "YYYY-MM-DD" | "2026-01-17" |
| Chart x-axis (weekly) | "ddd" | "Mon", "Tue" |
| Chart x-axis (monthly) | "D" | "1", "2", "15" |

---

## Summary

This specification covers:

- ✅ PostgreSQL schema with Docker
- ✅ FastAPI REST endpoints
- ✅ Next.js + React + shadcn/ui frontend
- ✅ Dashboard with charts (Recharts)
- ✅ Expense CRUD with filters
- ✅ Category management with "add new" in dropdown
- ✅ Recurring expenses with reminders
- ✅ CSV export
- ✅ Step-by-step implementation order

**No AI/LLM components** — purely manual input with clean UX.

---

*Ready for Claude Code / Codex to implement step by step.*
