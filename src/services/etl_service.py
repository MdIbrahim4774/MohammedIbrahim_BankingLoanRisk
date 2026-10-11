import os
import shutil
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import SessionLocal, init_db
from src.models.db_models import (
    Customer, CreditProfile, Bill, Payment, SegmentKPISummary
)
from src.services.risk_service import risk_service
from src.services.data_quality_service import data_quality_service
from src.services.reconciliation_service import reconciliation_service

logger = logging.getLogger("banking_loan.etl")

# Ensure pipeline directories exist
os.makedirs(settings.RAW_DATA_DIR, exist_ok=True)
os.makedirs(settings.PROCESSED_DATA_DIR, exist_ok=True)

# Month mapping for 6-month historical billing cycles (April 2005 to Sept 2005)
MONTH_MAPPINGS = [
    (1, "2005-09", "BILL_AMT1", "PAY_AMT1", "PAY_0"),
    (2, "2005-08", "BILL_AMT2", "PAY_AMT2", "PAY_2"),
    (3, "2005-07", "BILL_AMT3", "PAY_AMT3", "PAY_3"),
    (4, "2005-06", "BILL_AMT4", "PAY_AMT4", "PAY_4"),
    (5, "2005-05", "BILL_AMT5", "PAY_AMT5", "PAY_5"),
    (6, "2005-04", "BILL_AMT6", "PAY_AMT6", "PAY_6")
]

def decode_gender(code: int) -> str:
    return "Male" if code == 1 else "Female" if code == 2 else "Unknown"

def decode_education(code: int) -> str:
    mapping = {
        1: "Graduate School",
        2: "University",
        3: "High School",
        4: "Others",
        5: "Unknown",
        6: "Unknown",
        0: "Unknown"
    }
    return mapping.get(int(code), "Others")

def decode_marriage(code: int) -> str:
    mapping = {
        1: "Married",
        2: "Single",
        3: "Others",
        0: "Others"
    }
    return mapping.get(int(code), "Others")

def get_age_group(age: int) -> str:
    if age < 30:
        return "20-29"
    elif age < 40:
        return "30-39"
    elif age < 50:
        return "40-49"
    elif age < 60:
        return "50-59"
    else:
        return "60+"

class ETLService:
    @staticmethod
    def get_pending_raw_files() -> List[str]:
        """
        Scan data/raw/ directory for unprocessed batch files (.xls, .xlsx, .csv).
        """
        os.makedirs(settings.RAW_DATA_DIR, exist_ok=True)
        valid_exts = (".xls", ".xlsx", ".csv")
        files = [
            f for f in os.listdir(settings.RAW_DATA_DIR)
            if f.lower().endswith(valid_exts) and not f.startswith(".")
        ]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(settings.RAW_DATA_DIR, x)))
        return files

    @staticmethod
    def get_processed_files() -> List[str]:
        """
        Scan data/processed/ directory for archived batch files.
        """
        os.makedirs(settings.PROCESSED_DATA_DIR, exist_ok=True)
        files = [f for f in os.listdir(settings.PROCESSED_DATA_DIR) if not f.startswith(".")]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(settings.PROCESSED_DATA_DIR, x)), reverse=True)
        return files

    @classmethod
    def load_raw_dataset(cls, file_path: Optional[str] = None, limit_rows: Optional[int] = None) -> Tuple[pd.DataFrame, str]:
        """
        Extract raw data from Excel or CSV file in data/raw/.
        Returns (DataFrame, resolved_file_path).
        """
        os.makedirs(settings.RAW_DATA_DIR, exist_ok=True)
        os.makedirs(settings.PROCESSED_DATA_DIR, exist_ok=True)

        resolved_path = None
        if file_path:
            # Check data/raw/ first
            raw_candidate = os.path.join(settings.RAW_DATA_DIR, os.path.basename(file_path))
            if os.path.exists(raw_candidate):
                resolved_path = os.path.abspath(raw_candidate)
            elif os.path.exists(file_path):
                resolved_path = os.path.abspath(file_path)
            else:
                raise FileNotFoundError(
                    f"File '{file_path}' was not found in '{settings.RAW_DATA_DIR}/' or at the specified path."
                )
        else:
            # Pick first available file from data/raw/
            pending = cls.get_pending_raw_files()
            if pending:
                resolved_path = os.path.abspath(os.path.join(settings.RAW_DATA_DIR, pending[0]))
            else:
                raise FileNotFoundError(
                    f"No pending data files found in '{settings.RAW_DATA_DIR}/'. "
                    f"Please place a new batch of data (.xls, .xlsx, or .csv) into '{settings.RAW_DATA_DIR}/' to process."
                )

        logger.info(f"Loading raw batch from {resolved_path}")
        
        if resolved_path.lower().endswith((".xls", ".xlsx")):
            # UCI dataset has column headers on row 1 (0-indexed 1)
            df = pd.read_excel(resolved_path, header=1)
        else:
            df = pd.read_csv(resolved_path)

        # Standardize column naming
        df.columns = [c.strip().replace(" ", "_").replace(".", "_") for c in df.columns]
        if "default_payment_next_month" not in df.columns:
            for c in df.columns:
                if "default" in c.lower():
                    df.rename(columns={c: "default_payment_next_month"}, inplace=True)
                    break

        if limit_rows:
            df = df.head(limit_rows)

        return df, resolved_path

    @classmethod
    def run_pipeline(
        cls,
        db: Session,
        mode: str = "batch",
        file_path: Optional[str] = None,
        custom_rows: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes ETL pipeline for a pending batch in data/raw/:
        1. Extract data from raw/
        2. Run data quality checks
        3. Transform & upsert into MySQL
        4. Recompute segment KPIs
        5. Run reconciliation audit
        6. Move processed file from data/raw/ to data/processed/
        """
        start_time = time.time()
        batch_id = f"ETL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        logger.info(f"Starting ETL Pipeline [Batch: {batch_id}]")

        init_db()

        # 1. EXTRACT
        df, source_path = cls.load_raw_dataset(file_path=file_path, limit_rows=custom_rows)
        source_count = len(df)
        raw_filename = os.path.basename(source_path)
        logger.info(f"Extracted {source_count} records from '{raw_filename}'.")

        # 2. DATA QUALITY VALIDATION
        dq_results = data_quality_service.run_all_checks(df, batch_id, db=db)
        logger.info(f"Completed {len(dq_results)} data-quality audits.")

        # 3. TRANSFORM & LOAD
        inserted_count = 0
        updated_count = 0

        # Pre-fetch existing customer IDs for fast upsert check
        candidate_ids = [int(x) for x in df['ID'].tolist()]
        existing_customers = {
            c.customer_id: c for c in db.query(Customer).filter(Customer.customer_id.in_(candidate_ids)).all()
        }

        for _, row in df.iterrows():
            cid = int(row['ID'])
            sex = int(row['SEX'])
            edu = int(row['EDUCATION'])
            mar = int(row['MARRIAGE'])
            age = int(row['AGE'])
            limit_bal = float(row['LIMIT_BAL'])
            default_val = int(row.get('default_payment_next_month', 0))

            # Collect historical sequences
            pay_statuses = [int(row.get(m[4], 0)) for m in MONTH_MAPPINGS]
            bill_amounts = [float(row.get(m[2], 0.0)) for m in MONTH_MAPPINGS]
            pay_amounts = [float(row.get(m[3], 0.0)) for m in MONTH_MAPPINGS]

            # Risk evaluation
            risk_eval = risk_service.evaluate_risk(
                limit_bal=limit_bal,
                pay_statuses=pay_statuses,
                bill_amounts=bill_amounts,
                pay_amounts=pay_amounts,
                default_next_month=default_val
            )

            if cid in existing_customers:
                # Update existing customer
                cust = existing_customers[cid]
                cust.sex = sex
                cust.sex_label = decode_gender(sex)
                cust.education = edu
                cust.education_label = decode_education(edu)
                cust.marriage = mar
                cust.marriage_label = decode_marriage(mar)
                cust.age = age
                cust.age_group = get_age_group(age)
                cust.updated_at = datetime.utcnow()

                # Update or create profile
                profile = cust.credit_profile
                if not profile:
                    profile = CreditProfile(customer_id=cid)
                    db.add(profile)

                profile.limit_bal = limit_bal
                profile.default_payment_next_month = default_val
                profile.risk_score = risk_eval["risk_score"]
                profile.risk_band = risk_eval["risk_band"]
                profile.utilization_ratio = risk_eval["utilization_ratio"]
                profile.max_delay_months = risk_eval["max_delay_months"]
                profile.avg_bill_amt = risk_eval["avg_bill_amt"]
                profile.avg_pay_amt = risk_eval["avg_pay_amt"]
                profile.repayment_ratio = risk_eval["repayment_ratio"]
                profile.requires_manual_review = risk_eval["requires_manual_review"]
                profile.review_reasons = " | ".join(risk_eval["review_reasons"])
                profile.updated_at = datetime.utcnow()

                # Clear and reload bills and payments for this customer
                db.query(Bill).filter(Bill.customer_id == cid).delete()
                db.query(Payment).filter(Payment.customer_id == cid).delete()

                updated_count += 1
            else:
                # Insert new customer
                cust = Customer(
                    customer_id=cid,
                    sex=sex,
                    sex_label=decode_gender(sex),
                    education=edu,
                    education_label=decode_education(edu),
                    marriage=mar,
                    marriage_label=decode_marriage(mar),
                    age=age,
                    age_group=get_age_group(age)
                )
                db.add(cust)

                profile = CreditProfile(
                    customer_id=cid,
                    limit_bal=limit_bal,
                    default_payment_next_month=default_val,
                    risk_score=risk_eval["risk_score"],
                    risk_band=risk_eval["risk_band"],
                    utilization_ratio=risk_eval["utilization_ratio"],
                    max_delay_months=risk_eval["max_delay_months"],
                    avg_bill_amt=risk_eval["avg_bill_amt"],
                    avg_pay_amt=risk_eval["avg_pay_amt"],
                    repayment_ratio=risk_eval["repayment_ratio"],
                    requires_manual_review=risk_eval["requires_manual_review"],
                    review_reasons=" | ".join(risk_eval["review_reasons"])
                )
                db.add(profile)

                inserted_count += 1

            # Insert bills and payments
            for m_idx, m_name, b_col, p_col, s_col in MONTH_MAPPINGS:
                b_val = float(row.get(b_col, 0.0))
                p_val = float(row.get(p_col, 0.0))
                s_val = int(row.get(s_col, 0))

                bill_obj = Bill(
                    customer_id=cid,
                    month_idx=m_idx,
                    month_name=m_name,
                    bill_amt=b_val
                )
                pay_obj = Payment(
                    customer_id=cid,
                    month_idx=m_idx,
                    month_name=m_name,
                    pay_amt=p_val,
                    pay_status=s_val
                )
                db.add(bill_obj)
                db.add(pay_obj)

        db.commit()

        # 4. RECOMPUTE PRE-AGGREGATED SEGMENT KPIS
        cls.recompute_segment_kpis(db)

        duration = round(time.time() - start_time, 2)

        # 5. RECONCILIATION AUDIT
        recon_audit = reconciliation_service.reconcile(
            db=db,
            batch_id=batch_id,
            df_source=df,
            inserted_count=inserted_count,
            updated_count=updated_count,
            duration_sec=duration
        )

        # 6. MOVE PROCESSED FILE FROM data/raw/ TO data/processed/
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dest_filename = f"{timestamp}_{raw_filename}"
        dest_path = os.path.abspath(os.path.join(settings.PROCESSED_DATA_DIR, dest_filename))

        # Check candidate file paths to move
        target_in_raw = os.path.abspath(os.path.join(settings.RAW_DATA_DIR, raw_filename))
        candidate_to_move = None
        if os.path.exists(source_path):
            candidate_to_move = os.path.abspath(source_path)
        elif os.path.exists(target_in_raw):
            candidate_to_move = target_in_raw

        if candidate_to_move and os.path.exists(candidate_to_move):
            try:
                shutil.move(candidate_to_move, dest_path)
                logger.info(f"Moved processed file from '{candidate_to_move}' to '{dest_path}'")
                if os.path.exists(target_in_raw) and target_in_raw != dest_path:
                    os.remove(target_in_raw)
            except Exception as e:
                logger.warning(f"Could not move file to processed directory: {e}")
                dest_path = candidate_to_move
        else:
            dest_path = source_path

        remaining_pending = len(cls.get_pending_raw_files())
        logger.info(
            f"ETL completed in {duration}s. Inserted: {inserted_count}, Updated: {updated_count}, "
            f"Reconciled: {recon_audit['reconciled']}. Remaining raw batches: {remaining_pending}."
        )

        return {
            "batch_id": batch_id,
            "mode": mode,
            "source_file": raw_filename,
            "processed_file_path": dest_path,
            "source_count": source_count,
            "loaded_count": recon_audit["loaded_count"],
            "inserted_count": inserted_count,
            "updated_count": updated_count,
            "reconciled": recon_audit["reconciled"],
            "duration_sec": duration,
            "data_quality_checks": len(dq_results),
            "remaining_raw_batches": remaining_pending,
            "message": f"Successfully processed {source_count} records from '{raw_filename}'. File archived to '{settings.PROCESSED_DATA_DIR}/'."
        }

    @staticmethod
    def recompute_segment_kpis(db: Session):
        """
        Recalculates fast materialized reporting tables for education, age groups, and marriage segments.
        """
        db.query(SegmentKPISummary).delete()

        def aggregate_by(group_attr_name: str, segment_type: str):
            results = (
                db.query(
                    getattr(Customer, group_attr_name).label("seg_val"),
                    Customer.customer_id,
                    CreditProfile.limit_bal,
                    CreditProfile.avg_bill_amt,
                    CreditProfile.avg_pay_amt,
                    CreditProfile.utilization_ratio,
                    CreditProfile.default_payment_next_month,
                    CreditProfile.risk_band
                )
                .join(CreditProfile, Customer.customer_id == CreditProfile.customer_id)
                .all()
            )
            
            if not results:
                return

            df_res = pd.DataFrame(results, columns=[
                "seg_val", "customer_id", "limit_bal", "avg_bill_amt", 
                "avg_pay_amt", "utilization_ratio", "default_val", "risk_band"
            ])

            for val, grp in df_res.groupby("seg_val"):
                count = len(grp)
                summary = SegmentKPISummary(
                    segment_type=segment_type,
                    segment_value=str(val),
                    customer_count=count,
                    avg_limit_bal=round(float(grp["limit_bal"].mean()), 2),
                    avg_bill_amt=round(float(grp["avg_bill_amt"].mean()), 2),
                    avg_pay_amt=round(float(grp["avg_pay_amt"].mean()), 2),
                    avg_utilization=round(float(grp["utilization_ratio"].mean()), 4),
                    default_rate=round(float(grp["default_val"].mean()), 4),
                    high_risk_pct=round(float((grp["risk_band"] == "High").mean()), 4),
                    updated_at=datetime.utcnow()
                )
                db.add(summary)

        aggregate_by("education_label", "education")
        aggregate_by("age_group", "age_group")
        aggregate_by("marriage_label", "marriage")
        aggregate_by("sex_label", "gender")
        db.commit()

etl_service = ETLService()
