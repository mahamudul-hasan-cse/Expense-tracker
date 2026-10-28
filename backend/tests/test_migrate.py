"""The deploy-time migration runner (python -m app.migrate)."""

from sqlalchemy import text

from app import migrate
from app.database import engine


def test_migrate_is_safe_to_rerun_and_releases_its_lock():
    migrate.main()  # the test DB is already at head: nothing to do, no error
    migrate.main()
    with engine.connect() as conn:
        # Another instance could take the lock now (it wasn't left held)
        assert conn.execute(text("SELECT pg_try_advisory_lock(:id)"), {"id": migrate.MIGRATION_LOCK_ID}).scalar()
        conn.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": migrate.MIGRATION_LOCK_ID})
