"""Run `alembic upgrade head` safely on deploy: python -m app.migrate

Holds a Postgres advisory lock while migrating, so if several instances start at once
only one migrates and the others wait, then find nothing left to do.
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.logging_config import configure_logging

# Any fixed 64-bit number, the same in every instance
MIGRATION_LOCK_ID = 726_160_401

logger = logging.getLogger("app.migrate")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=settings.app_env == "production")
    alembic_cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    with engine.connect() as conn:
        conn.execute(text("SELECT pg_advisory_lock(:id)"), {"id": MIGRATION_LOCK_ID})
        try:
            command.upgrade(alembic_cfg, "head")
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": MIGRATION_LOCK_ID})
    logger.info("Database is up to date")


if __name__ == "__main__":
    main()
