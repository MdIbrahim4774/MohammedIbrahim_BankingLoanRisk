import logging
from apscheduler.schedulers.background import BackgroundScheduler
from src.core.database import SessionLocal
from src.services.etl_service import etl_service
from src.utils.logger import app_logger

scheduler = BackgroundScheduler()

def scheduled_incremental_batch_job():
    """
    Scheduled job: executes periodic ETL batch updates when new data is placed in data/raw/.
    """
    pending = etl_service.get_pending_raw_files()
    if not pending:
        app_logger.info("[Scheduler] No pending raw data batches found in data/raw/.")
        return

    app_logger.info(f"[Scheduler] Found {len(pending)} pending batch(es) in data/raw/. Processing oldest: {pending[0]}")
    db = SessionLocal()
    try:
        result = etl_service.run_pipeline(db=db, mode="batch")
        app_logger.info(f"[Scheduler] ETL batch completed: {result['message']}")
    except Exception as e:
        app_logger.error(f"[Scheduler] Error during scheduled ETL execution: {e}")
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        # Schedule incremental batch sync every 6 hours (configurable)
        scheduler.add_job(
            scheduled_incremental_batch_job,
            trigger="interval",
            hours=6,
            id="incremental_etl_batch_job",
            replace_existing=True
        )
        scheduler.start()
        app_logger.info("[Scheduler] Background scheduler started successfully.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        app_logger.info("[Scheduler] Background scheduler shut down.")

