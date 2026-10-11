import json
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
from sqlalchemy.orm import Session
from src.models.db_models import DataQualityLog

class DataQualityService:
    @staticmethod
    def run_all_checks(df: pd.DataFrame, batch_id: str, db: Session = None) -> List[Dict[str, Any]]:
        """
        Execute comprehensive data-quality checks on customer credit dataset.
        Returns a list of check results and persists them to DB if session provided.
        """
        results = []
        total_records = len(df)

        # 1. Duplicate Check
        dup_count = int(df.duplicated(subset=['ID']).sum()) if 'ID' in df.columns else 0
        dup_status = "PASS" if dup_count == 0 else "FAIL"
        dup_res = {
            "batch_id": batch_id,
            "check_name": "Unique Customer ID Validation",
            "status": dup_status,
            "records_checked": total_records,
            "failed_count": dup_count,
            "details": f"Found {dup_count} duplicate customer IDs."
        }
        results.append(dup_res)

        # 2. Credit Limit Range Check (LIMIT_BAL > 0 and reasonable range)
        if 'LIMIT_BAL' in df.columns:
            invalid_limits = int((df['LIMIT_BAL'] <= 0).sum() + (df['LIMIT_BAL'] > 5000000).sum())
            limit_status = "PASS" if invalid_limits == 0 else "FAIL"
            results.append({
                "batch_id": batch_id,
                "check_name": "Credit Limit Range Check",
                "status": limit_status,
                "records_checked": total_records,
                "failed_count": invalid_limits,
                "details": f"{invalid_limits} records with non-positive or out-of-range credit limits."
            })

        # 3. Demographic Age Range Check (18 <= AGE <= 100)
        if 'AGE' in df.columns:
            invalid_age = int(((df['AGE'] < 18) | (df['AGE'] > 100)).sum())
            age_status = "PASS" if invalid_age == 0 else "FAIL"
            results.append({
                "batch_id": batch_id,
                "check_name": "Customer Age Range Check",
                "status": age_status,
                "records_checked": total_records,
                "failed_count": invalid_age,
                "details": f"{invalid_age} records with age outside [18, 100]."
            })

        # 4. Gender Category Check (SEX in [1, 2])
        if 'SEX' in df.columns:
            invalid_sex = int((~df['SEX'].isin([1, 2])).sum())
            sex_status = "PASS" if invalid_sex == 0 else "FAIL"
            results.append({
                "batch_id": batch_id,
                "check_name": "Gender Categorical Code Validation",
                "status": sex_status,
                "records_checked": total_records,
                "failed_count": invalid_sex,
                "details": f"{invalid_sex} records with invalid gender codes."
            })

        # 5. Education & Marriage Codes
        if 'EDUCATION' in df.columns:
            # Documented 1-4, but 0, 5, 6 exist in real data (unknowns)
            undocumented_edu = int((~df['EDUCATION'].isin([0, 1, 2, 3, 4, 5, 6])).sum())
            results.append({
                "batch_id": batch_id,
                "check_name": "Education Domain Validation",
                "status": "PASS" if undocumented_edu == 0 else "WARNING",
                "records_checked": total_records,
                "failed_count": undocumented_edu,
                "details": f"{undocumented_edu} records with unknown education encoding outside allowed domain."
            })

        if 'MARRIAGE' in df.columns:
            undocumented_mar = int((~df['MARRIAGE'].isin([0, 1, 2, 3])).sum())
            results.append({
                "batch_id": batch_id,
                "check_name": "Marital Status Domain Validation",
                "status": "PASS" if undocumented_mar == 0 else "WARNING",
                "records_checked": total_records,
                "failed_count": undocumented_mar,
                "details": f"{undocumented_mar} records with unknown marital status encoding."
            })

        # 6. Repayment Status Range Check (-2 to 9)
        pay_cols = [c for c in ['PAY_0', 'PAY_2', 'PAY_3', 'PAY_4', 'PAY_5', 'PAY_6'] if c in df.columns]
        if pay_cols:
            invalid_pays = int(((df[pay_cols] < -2) | (df[pay_cols] > 9)).any(axis=1).sum())
            results.append({
                "batch_id": batch_id,
                "check_name": "Repayment Status Range Check (-2 to 9)",
                "status": "PASS" if invalid_pays == 0 else "FAIL",
                "records_checked": total_records,
                "failed_count": invalid_pays,
                "details": f"{invalid_pays} records with out-of-bounds repayment status codes."
            })

        # 7. Payment Consistency Check (pay amount vs limit)
        pay_amt_cols = [c for c in ['PAY_AMT1', 'PAY_AMT2', 'PAY_AMT3', 'PAY_AMT4', 'PAY_AMT5', 'PAY_AMT6'] if c in df.columns]
        if pay_amt_cols and 'LIMIT_BAL' in df.columns:
            suspicious_pays = int((df[pay_amt_cols].max(axis=1) > df['LIMIT_BAL'] * 5).sum())
            results.append({
                "batch_id": batch_id,
                "check_name": "Financial Sanity Check (Payment vs Limit)",
                "status": "PASS" if suspicious_pays == 0 else "WARNING",
                "records_checked": total_records,
                "failed_count": suspicious_pays,
                "details": f"{suspicious_pays} records with individual payment exceeding 5x total credit limit."
            })

        # Save to database if db session provided
        if db:
            for item in results:
                db_log = DataQualityLog(
                    batch_id=item["batch_id"],
                    check_name=item["check_name"],
                    status=item["status"],
                    records_checked=item["records_checked"],
                    failed_count=item["failed_count"],
                    details=item["details"],
                    created_at=datetime.utcnow()
                )
                db.add(db_log)
            db.commit()

        return results

data_quality_service = DataQualityService()

