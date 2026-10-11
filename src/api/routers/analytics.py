from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.core.database import get_db
from src.core.security import get_current_user
from src.models.db_models import (
    Customer, CreditProfile, Bill, Payment, SegmentKPISummary
)
from src.models.schemas import OverallKPIs, SegmentKPIItem, MonthlyTrendItem

router = APIRouter(prefix="/analytics", tags=["Analytics & KPIs"])

@router.get("/kpis", response_model=OverallKPIs)
def get_portfolio_kpis(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get aggregated portfolio-level KPIs including total exposure, utilization, default rates, and risk bands.
    """
    total_cust = db.query(Customer).count()
    if total_cust == 0:
        return OverallKPIs(
            total_customers=0,
            total_credit_exposure=0.0,
            avg_credit_limit=0.0,
            overall_default_rate=0.0,
            high_risk_customers_pct=0.0,
            avg_utilization_ratio=0.0,
            avg_repayment_ratio=0.0,
            pending_manual_reviews=0
        )

    exposure_sum = db.query(func.sum(CreditProfile.limit_bal)).scalar() or 0.0
    avg_limit = db.query(func.avg(CreditProfile.limit_bal)).scalar() or 0.0
    default_count = db.query(CreditProfile).filter(CreditProfile.default_payment_next_month == 1).count()
    high_risk_count = db.query(CreditProfile).filter(CreditProfile.risk_band == "High").count()
    avg_util = db.query(func.avg(CreditProfile.utilization_ratio)).scalar() or 0.0
    avg_repay = db.query(func.avg(CreditProfile.repayment_ratio)).scalar() or 0.0
    pending_reviews = db.query(CreditProfile).filter(
        CreditProfile.requires_manual_review == True,
        CreditProfile.manual_review_status == "PENDING"
    ).count()

    return OverallKPIs(
        total_customers=total_cust,
        total_credit_exposure=round(float(exposure_sum), 2),
        avg_credit_limit=round(float(avg_limit), 2),
        overall_default_rate=round(float(default_count / total_cust) * 100, 2),
        high_risk_customers_pct=round(float(high_risk_count / total_cust) * 100, 2),
        avg_utilization_ratio=round(float(avg_util), 4),
        avg_repayment_ratio=round(float(avg_repay), 4),
        pending_manual_reviews=pending_reviews
    )

@router.get("/segments", response_model=List[SegmentKPIItem])
def get_segment_kpis(
    segment_type: Optional[str] = Query(None, description="education, age_group, marriage, gender"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get demographic segment KPIs (utilization, default rates, high-risk percentages).
    Uses the accelerated segment_kpi_summaries table.
    """
    query = db.query(SegmentKPISummary)
    if segment_type:
        query = query.filter(SegmentKPISummary.segment_type == segment_type)

    summaries = query.all()
    results = []
    for s in summaries:
        results.append(SegmentKPIItem(
            segment_type=s.segment_type,
            segment_value=s.segment_value,
            customer_count=s.customer_count,
            avg_limit_bal=s.avg_limit_bal,
            avg_bill_amt=s.avg_bill_amt,
            avg_pay_amt=s.avg_pay_amt,
            avg_utilization=s.avg_utilization,
            default_rate=round(s.default_rate * 100, 2),
            high_risk_pct=round(s.high_risk_pct * 100, 2)
        ))
    return results

@router.get("/trends", response_model=List[MonthlyTrendItem])
def get_monthly_cashflow_trends(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get 6-month historical cashflow trends (billed amount vs repaid amount and delinquency rate).
    """
    results = []
    # 6 billing cycles
    for m_idx in range(1, 7):
        bill_stats = db.query(
            func.sum(Bill.bill_amt),
            func.avg(Bill.bill_amt),
            func.max(Bill.month_name)
        ).filter(Bill.month_idx == m_idx).first()

        pay_stats = db.query(
            func.sum(Payment.pay_amt),
            func.avg(Payment.pay_amt)
        ).filter(Payment.month_idx == m_idx).first()

        total_bills = db.query(Payment).filter(Payment.month_idx == m_idx).count()
        delinquent_bills = db.query(Payment).filter(Payment.month_idx == m_idx, Payment.pay_status > 0).count()
        delinq_rate = (delinquent_bills / total_bills * 100) if total_bills > 0 else 0.0

        m_name = bill_stats[2] if bill_stats and bill_stats[2] else f"Month {m_idx}"
        tot_b = float(bill_stats[0] or 0.0) if bill_stats else 0.0
        avg_b = float(bill_stats[1] or 0.0) if bill_stats else 0.0
        tot_p = float(pay_stats[0] or 0.0) if pay_stats else 0.0
        avg_p = float(pay_stats[1] or 0.0) if pay_stats else 0.0

        results.append(MonthlyTrendItem(
            month_idx=m_idx,
            month_name=m_name,
            total_bill_amount=round(tot_b, 2),
            total_pay_amount=round(tot_p, 2),
            avg_bill_amount=round(avg_b, 2),
            avg_pay_amount=round(avg_p, 2),
            delinquent_rate=round(delinq_rate, 2)
        ))

    # Sort chronological (Month 6=April to Month 1=Sept)
    results.sort(key=lambda x: x.month_idx, reverse=True)
    return results

