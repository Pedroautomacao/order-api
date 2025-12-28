from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text

from app.dashboard.snapshot.services.dashboard_snapshot_service import (
    DashboardSnapshotService,
)
from app.database.session import SessionLocal
from app.core.logging import logger

# Chave fixa do advisory lock (documentada)
DASHBOARD_SNAPSHOT_LOCK_KEY = 987654321


def start_scheduler():
    scheduler = BackgroundScheduler()

    def generate_dashboard_snapshot():
        db = SessionLocal()

        logger.info("Dashboard snapshot job started")

        try:
            lock_acquired = db.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": DASHBOARD_SNAPSHOT_LOCK_KEY},
            ).scalar()

            if not lock_acquired:
                logger.info(
                    "Dashboard snapshot skipped (lock not acquired)"
                )
                return

            snapshot = DashboardSnapshotService.generate(db)

            logger.info(
                "Dashboard snapshot job finished",
                extra={"snapshot_id": snapshot.id},
            )

        except Exception:
            logger.exception("Dashboard snapshot job failed")
            raise

        finally:
            db.close()

    scheduler.add_job(
        generate_dashboard_snapshot,
        trigger="interval",
        minutes=1,
        id="dashboard_snapshot_job",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
