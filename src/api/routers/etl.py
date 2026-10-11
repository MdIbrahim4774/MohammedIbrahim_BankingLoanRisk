from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.core.database import get_db
from src.core.security import get_current_user, require_role
from src.models.db_models import ETLReconciliationLog, DataQualityLog
from src.models.schemas import (
    ETLRunRequest, ETLRunResponse, ReconciliationLogResponse, DataQualityLogResponse
)
from src.services.etl_service import etl_service

router = APIRouter(prefix="/etl", tags=["ETL Pipeline & Data Quality"])

@router.get("/batches", response_model=Dict[str, List[str]])
def get_batch_file_status(current_user: dict = Depends(get_current_user)):
    """
    Get lists of pending raw batches waiting in data/raw/ and archived files in data/processed/.
    """
    return {
        "pending_raw_files": etl_service.get_pending_raw_files(),
        "processed_files": etl_service.get_processed_files()
    }

@router.post("/run", response_model=ETLRunResponse)
def trigger_etl_pipeline(
    payload: ETLRunRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("administrator"))
):
    """
    Trigger ETL pipeline execution for a raw batch in data/raw/.
    Processes the batch into MySQL and moves the file to data/processed/. Admin only.
    """
    try:
        result = etl_service.run_pipeline(
            db=db,
            mode=payload.mode,
            file_path=payload.file_path,
            custom_rows=payload.custom_rows
        )
        return ETLRunResponse(
            batch_id=result["batch_id"],
            mode=result["mode"],
            source_file=result.get("source_file"),
            processed_file_path=result.get("processed_file_path"),
            source_count=result["source_count"],
            loaded_count=result["loaded_count"],
            reconciled=result["reconciled"],
            duration_sec=result["duration_sec"],
            remaining_raw_batches=result.get("remaining_raw_batches", 0),
            message=result["message"]
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ETL Execution failed: {str(e)}")

@router.get("/reconciliation", response_model=List[ReconciliationLogResponse])
def get_reconciliation_logs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch record-level ETL reconciliation audit logs.
    """
    logs = db.query(ETLReconciliationLog).order_by(desc(ETLReconciliationLog.created_at)).limit(limit).all()
    return [ReconciliationLogResponse.model_validate(log) for log in logs]

@router.get("/data-quality", response_model=List[DataQualityLogResponse])
def get_data_quality_logs(
    batch_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch data quality validation results.
    """
    query = db.query(DataQualityLog)
    if batch_id:
        query = query.filter(DataQualityLog.batch_id == batch_id)

    logs = query.order_by(desc(DataQualityLog.created_at)).limit(limit).all()
    return [DataQualityLogResponse.model_validate(log) for log in logs]
