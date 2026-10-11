import pytest
import pandas as pd
from src.services.data_quality_service import data_quality_service
from src.services.reconciliation_service import reconciliation_service
from src.core.database import SessionLocal, init_db

def test_data_quality_checks():
    test_data = {
        'ID': [1, 2, 3],
        'LIMIT_BAL': [50000.0, 100000.0, -500.0],  # -500 is invalid limit
        'SEX': [1, 2, 5],                          # 5 is invalid gender
        'EDUCATION': [1, 2, 3],
        'MARRIAGE': [1, 2, 1],
        'AGE': [25, 120, 30],                      # 120 is out of range
        'PAY_0': [0, 15, -1],                      # 15 is out of bounds
        'BILL_AMT1': [1000, 2000, 3000],
        'PAY_AMT1': [1000, 2000, 3000]
    }
    df = pd.DataFrame(test_data)
    results = data_quality_service.run_all_checks(df, batch_id="TEST-BATCH")
    
    assert len(results) > 0
    checks_map = {r["check_name"]: r for r in results}
    
    assert checks_map["Credit Limit Range Check"]["status"] == "FAIL"
    assert checks_map["Customer Age Range Check"]["status"] == "FAIL"
    assert checks_map["Gender Categorical Code Validation"]["status"] == "FAIL"

def test_reconciliation_checksum_generation():
    test_data = {
        'ID': [1, 2],
        'LIMIT_BAL': [50000.0, 100000.0],
        'BILL_AMT1': [1000.0, 2000.0],
        'BILL_AMT2': [1000.0, 2000.0],
        'BILL_AMT3': [1000.0, 2000.0],
        'BILL_AMT4': [1000.0, 2000.0],
        'BILL_AMT5': [1000.0, 2000.0],
        'BILL_AMT6': [1000.0, 2000.0],
    }
    df = pd.DataFrame(test_data)
    checksum = reconciliation_service.calculate_source_checksum(df)
    assert isinstance(checksum, str)
    assert len(checksum) == 32  # MD5 hex length

