import os
import shutil
import pytest
import pandas as pd
from src.core.config import settings
from src.core.database import SessionLocal, init_db
from src.services.etl_service import (
    etl_service, decode_gender, decode_education, decode_marriage, get_age_group
)
from src.models.db_models import Customer, CreditProfile
from tests.conftest import requires_mysql

def test_demographic_decoders():
    assert decode_gender(1) == "Male"
    assert decode_gender(2) == "Female"
    assert decode_education(1) == "Graduate School"
    assert decode_education(2) == "University"
    assert decode_education(3) == "High School"
    assert decode_marriage(1) == "Married"
    assert decode_marriage(2) == "Single"
    assert get_age_group(25) == "20-29"
    assert get_age_group(35) == "30-39"
    assert get_age_group(65) == "60+"

def test_raw_and_processed_directory_structure():
    assert os.path.exists(settings.RAW_DATA_DIR)
    assert os.path.exists(settings.PROCESSED_DATA_DIR)
    
    # Create temporary dummy file in raw
    dummy_file = os.path.join(settings.RAW_DATA_DIR, "_test_dummy.csv")
    with open(dummy_file, "w") as f:
        f.write("ID,LIMIT_BAL\n1,10000\n")
    
    pending = etl_service.get_pending_raw_files()
    assert "_test_dummy.csv" in pending
    
    # Clean up dummy
    if os.path.exists(dummy_file):
        os.remove(dummy_file)

@requires_mysql
def test_etl_batch_run_and_archive():
    init_db()
    db = SessionLocal()
    
    # Create a small valid test batch in raw
    test_raw_path = os.path.join(settings.RAW_DATA_DIR, "_test_pipeline_batch.csv")
    df_test = pd.DataFrame({
        "ID": [88801, 88802],
        "LIMIT_BAL": [100000.0, 150000.0],
        "SEX": [1, 2],
        "EDUCATION": [1, 2],
        "MARRIAGE": [1, 2],
        "AGE": [30, 35],
        "PAY_0": [0, 0],
        "PAY_2": [0, 0],
        "PAY_3": [0, 0],
        "PAY_4": [0, 0],
        "PAY_5": [0, 0],
        "PAY_6": [0, 0],
        "BILL_AMT1": [10000.0, 20000.0],
        "BILL_AMT2": [10000.0, 20000.0],
        "BILL_AMT3": [10000.0, 20000.0],
        "BILL_AMT4": [10000.0, 20000.0],
        "BILL_AMT5": [10000.0, 20000.0],
        "BILL_AMT6": [10000.0, 20000.0],
        "PAY_AMT1": [10000.0, 20000.0],
        "PAY_AMT2": [10000.0, 20000.0],
        "PAY_AMT3": [10000.0, 20000.0],
        "PAY_AMT4": [10000.0, 20000.0],
        "PAY_AMT5": [10000.0, 20000.0],
        "PAY_AMT6": [10000.0, 20000.0],
        "default_payment_next_month": [0, 0]
    })
    df_test.to_csv(test_raw_path, index=False)
    
    try:
        result = etl_service.run_pipeline(db=db, mode="batch", file_path="_test_pipeline_batch.csv")
        assert result["source_count"] == 2
        assert result["reconciled"] is True
        
        # Verify file moved out of raw and into processed
        assert not os.path.exists(test_raw_path)
        assert os.path.exists(result["processed_file_path"])
        
        # Clean up archived test file
        if os.path.exists(result["processed_file_path"]):
            os.remove(result["processed_file_path"])
    finally:
        if os.path.exists(test_raw_path):
            os.remove(test_raw_path)
        db.close()
