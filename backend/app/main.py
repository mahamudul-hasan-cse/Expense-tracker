from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import categories, expenses, recurring, stats, export, budgets

settings = get_settings()

app = FastAPI(
    title="Wallet Agent API",
    description="A manual expense tracker API",
    version="1.0.0"
)

# CORS middleware
origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(categories.router, prefix="/api/v1")
app.include_router(expenses.router, prefix="/api/v1")
app.include_router(recurring.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")
app.include_router(budgets.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "Wallet Agent API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
