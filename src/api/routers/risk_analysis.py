from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.core.database import get_db
from src.core.security import get_current_user
from src.models.db_models import Customer, CreditProfile
from src.models.schemas import (
    RiskEvaluationRequest, RiskEvaluationResponse, PaginatedResponse, CustomerResponse, CreditProfileSchema
)
from src.services.risk_service import risk_service

router = APIRouter(prefix="/risk", tags=["Risk Analysis & Underwriting"])

@router.post("/evaluate", response_model=RiskEvaluationResponse)
def evaluate_loan_risk(data: RiskEvaluationRequest):
    """
    Real-time credit risk scoring and business-rule analysis.
    Evaluates risk score, Low/Medium/High bands, and manual review triggers.
    """
    res = risk_service.evaluate_risk(
        limit_bal=data.limit_bal,
        pay_statuses=data.pay_statuses,
        bill_amounts=data.bill_amounts,
        pay_amounts=data.pay_amounts
    )
    return RiskEvaluationResponse(**res)

@router.get("/review-queue", response_model=PaginatedResponse)
def get_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    review_status: Optional[str] = Query(None, description="PENDING, APPROVED, REJECTED"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get customer accounts flagged by business rules requiring manual underwriter review.
    """
    query = (
        db.query(Customer)
        .join(CreditProfile, Customer.customer_id == CreditProfile.customer_id)
        .filter(CreditProfile.requires_manual_review == True)
    )

    if review_status:
        query = query.filter(CreditProfile.manual_review_status == review_status)

    query = query.order_by(desc(CreditProfile.risk_score))
    total = query.count()
    offset = (page - 1) * page_size
    customers = query.offset(offset).limit(page_size).all()

    items = []
    for c in customers:
        cp = c.credit_profile
        items.append(CustomerResponse(
            customer_id=c.customer_id,
            sex=c.sex,
            sex_label=c.sex_label,
            education=c.education,
            education_label=c.education_label,
            marriage=c.marriage,
            marriage_label=c.marriage_label,
            age=c.age,
            age_group=c.age_group,
            created_at=c.created_at,
            updated_at=c.updated_at,
            credit_profile=CreditProfileSchema.model_validate(cp) if cp else None
        ))

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.put("/review-queue/{customer_id}/status")
def update_review_status(
    customer_id: int,
    status: str = Body(..., embed=True, description="APPROVED, REJECTED, or PENDING"),
    notes: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update manual review status for an account (Analyst or Admin).
    """
    profile = db.query(CreditProfile).filter(CreditProfile.customer_id == customer_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Credit profile not found")

    valid_statuses = ["PENDING", "APPROVED", "REJECTED"]
    if status.upper() not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    profile.manual_review_status = status.upper()
    profile.reviewed_by = current_user.get("username", "analyst")
    profile.reviewed_at = datetime.utcnow()
    if notes:
        profile.review_reasons = (profile.review_reasons or "") + f" | Underwriter Notes: {notes}"

    db.commit()
    db.refresh(profile)

    return {
        "customer_id": customer_id,
        "manual_review_status": profile.manual_review_status,
        "reviewed_by": profile.reviewed_by,
        "reviewed_at": profile.reviewed_at
    }

