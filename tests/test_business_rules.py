import pytest
from src.services.risk_service import risk_service

def test_risk_evaluation_low_risk():
    # Client with 0 delays, low utilization (20%), and full repayments
    res = risk_service.evaluate_risk(
        limit_bal=100000.0,
        pay_statuses=[0, 0, 0, 0, 0, 0],
        bill_amounts=[20000.0, 20000.0, 20000.0, 20000.0, 20000.0, 20000.0],
        pay_amounts=[20000.0, 20000.0, 20000.0, 20000.0, 20000.0, 20000.0],
        default_next_month=0
    )
    assert res["risk_band"] == "Low"
    assert res["utilization_ratio"] == 0.20
    assert res["repayment_ratio"] == 1.0
    assert res["max_delay_months"] == 0
    assert res["requires_manual_review"] is False
    assert res["approval_recommendation"] == "STANDARD_APPROVAL"

def test_risk_evaluation_high_risk_delinquency():
    # Client with 2+ months delay
    res = risk_service.evaluate_risk(
        limit_bal=50000.0,
        pay_statuses=[2, 2, 1, 0, 0, 0],
        bill_amounts=[45000.0, 45000.0, 45000.0, 40000.0, 30000.0, 20000.0],
        pay_amounts=[1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0],
        default_next_month=1
    )
    assert res["risk_band"] == "High"
    assert res["max_delay_months"] == 2
    assert res["risk_score"] >= 65.0

def test_manual_review_triggers():
    # High credit exposure (NT$600,000) with payment delay
    res = risk_service.evaluate_risk(
        limit_bal=600000.0,
        pay_statuses=[1, 0, 0, 0, 0, 0],
        bill_amounts=[200000.0, 180000.0, 150000.0, 100000.0, 50000.0, 20000.0],
        pay_amounts=[5000.0, 5000.0, 5000.0, 5000.0, 5000.0, 5000.0]
    )
    assert res["requires_manual_review"] is True
    assert any("High credit limit exposure" in r for r in res["review_reasons"])

