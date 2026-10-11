import hashlib
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy.orm import Session
from src.models.db_models import ETLReconciliationLog, Customer, CreditProfile

class ReconciliationService:
    @staticmethod
    def calculate_source_checksum(df: pd.DataFrame) -> str:
        """
        Calculate cryptographic MD5 hash representing the source dataset content.
        Combines IDs, Limit balances, and bill sums.
        """
        id_series = df['ID'].astype(str) if 'ID' in df.columns else df.index.astype(str)
        limit_sum = float(df['LIMIT_BAL'].sum()) if 'LIMIT_BAL' in df.columns else 0.0
        
        bill_sum = 0.0
        for i in range(1, 7):
            col = f'BILL_AMT{i}'
            if col in df.columns:
                bill_sum += float(df[col].sum())

        signature = f"COUNT:{len(df)}|LIMITS:{limit_sum:.2f}|BILLS:{bill_sum:.2f}|SAMPLE_IDS:{id_series.iloc[:10].tolist()}"
        return hashlib.md5(signature.encode('utf-8')).hexdigest()

    @staticmethod
    def reconcile(
        db: Session,
        batch_id: str,
        df_source: pd.DataFrame,
        inserted_count: int,
        updated_count: int,
        duration_sec: float
    ) -> Dict[str, Any]:
        """
        Execute record-level reconciliation between extracted source dataset and relational tables.
        """
        source_count = len(df_source)
        source_checksum = ReconciliationService.calculate_source_checksum(df_source)

        # Query loaded database records for this slice or total
        loaded_count = db.query(Customer).count()

        # Target checksum representation
        target_limit_sum = float(db.query(CreditProfile.limit_bal).all() and sum(r[0] for r in db.query(CreditProfile.limit_bal).all()) or 0.0)
        target_signature = f"LOADED:{loaded_count}|TARGET_LIMITS:{target_limit_sum:.2f}"
        loaded_checksum = hashlib.md5(target_signature.encode('utf-8')).hexdigest()

        # Reconciliation assertion:
        # Check if source count matches inserted + updated or loaded count
        is_reconciled = (source_count <= loaded_count) and (inserted_count + updated_count == source_count)

        status_str = "SUCCESS" if is_reconciled else "DISCREPANCY_DETECTED"

        recon_log = ETLReconciliationLog(
            batch_id=batch_id,
            source_count=source_count,
            loaded_count=loaded_count,
            reconciled=is_reconciled,
            source_checksum=source_checksum,
            loaded_checksum=loaded_checksum,
            inserted_count=inserted_count,
            updated_count=updated_count,
            duration_sec=duration_sec,
            status=status_str,
            created_at=datetime.utcnow()
        )
        db.add(recon_log)
        db.commit()
        db.refresh(recon_log)

        return {
            "recon_id": recon_log.recon_id,
            "batch_id": batch_id,
            "source_count": source_count,
            "loaded_count": loaded_count,
            "reconciled": is_reconciled,
            "source_checksum": source_checksum,
            "loaded_checksum": loaded_checksum,
            "inserted_count": inserted_count,
            "updated_count": updated_count,
            "duration_sec": duration_sec,
            "status": status_str
        }

reconciliation_service = ReconciliationService()

