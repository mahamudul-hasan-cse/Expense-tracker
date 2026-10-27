import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings

# Fail fast with a readable message if configuration is missing or invalid
try:
    settings = get_settings()
except ValidationError as exc:
    raise SystemExit(f"Configuration error:\n{exc}") from None

from app.assistant import router as assistant_router  # noqa: E402
from app.database import get_db  # noqa: E402
from app.errors import error_response, register_error_handlers  # noqa: E402
from app.logging_config import configure_logging  # noqa: E402
from app.middleware import RequestLogMiddleware  # noqa: E402
from app.rate_limit import RateLimitMiddleware, limiter  # noqa: E402
from app.routers import (  # noqa: E402
    auth,
    budgets,
    categories,
    expenses,
    export,
    goals,
    income_categories,
    incomes,
    recurring,
    stats,
)

configure_logging(settings.log_level, json_logs=settings.app_env == "production")
logger = logging.getLogger("app")

app = FastAPI(title="Wallet Agent API", description="A manual expense tracker API", version="1.0.0")

app.state.limiter = limiter
register_error_handlers(app)

# Middleware runs bottom-up: request log (outermost) -> CORS -> rate limit -> app
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestLogMiddleware)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(expenses.router, prefix="/api/v1")
app.include_router(recurring.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")
app.include_router(budgets.router, prefix="/api/v1")
app.include_router(income_categories.router, prefix="/api/v1")
app.include_router(incomes.router, prefix="/api/v1")
app.include_router(goals.router, prefix="/api/v1")
app.include_router(assistant_router.router, prefix="/api/v1")

logger.info("API started", extra={"app_env": settings.app_env, "origins": settings.origins})


@app.get("/")
@limiter.exempt
def root(request: Request):
    return {"message": "Wallet Agent API", "version": "1.0.0"}


@app.get("/health")
@limiter.exempt
def health_check(request: Request, db: Session = Depends(get_db)):
    """Liveness + database check, for uptime monitors and load balancers."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("health check: database unreachable")
        return error_response(503, "Database unavailable")
    return {"status": "healthy", "database": "ok"}
