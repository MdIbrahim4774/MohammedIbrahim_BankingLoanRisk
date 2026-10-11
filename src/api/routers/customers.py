import csv
import io
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from src.core.database import get_db
from src.core.security import get_current_user, require_role
from src.models.db_models import Customer, CreditProfile, Bill, Payment
from src.models.schemas import (
    CustomerResponse, CustomerDetailResponse, CustomerCreate, CustomerUpdate,
    PaginatedResponse, CreditProfileSchema, BillSchema, PaymentSchema
)
from src.services.etl_service import decode_gender, decode_education, decode_marriage, get_age_group
from src.services.risk_service import risk_service

router = APIRouter(prefix="/customers", tags=["Customers Management"])

@router.get("", response_model=PaginatedResponse)
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    risk_band: Optional[str] = Query(None, description="Filter by risk band: Low, Medium, High"),
    education: Optional[str] = Query(None, description="Filter by education label"),
    age_group: Optional[str] = Query(None, description="Filter by age group (e.g. 20-29, 30-39)"),
    gender: Optional[str] = Query(None, description="Filter by gender (Male, Female)"),
    search_id: Optional[int] = Query(None, description="Search by specific Customer ID"),
    sort_by: str = Query("customer_id", description="customer_id, limit_bal, risk_score, age"),
    order: str = Query("asc", description="asc or desc"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List customers with pagination, multi-attribute filtering, and sorting.
    """
    query = db.query(Customer).outerjoin(CreditProfile, Customer.customer_id == CreditProfile.customer_id)

    if search_id is not None:
        query = query.filter(Customer.customer_id == search_id)
    if risk_band:
        query = query.filter(CreditProfile.risk_band == risk_band)
    if education:
        query = query.filter(Customer.education_label == education)
    if age_group:
        query = query.filter(Customer.age_group == age_group)
    if gender:
        query = query.filter(Customer.sex_label == gender)

    # Sorting
    sort_col = Customer.customer_id
    if sort_by == "limit_bal":
        sort_col = CreditProfile.limit_bal
    elif sort_by == "risk_score":
        sort_col = CreditProfile.risk_score
    elif sort_by == "age":
        sort_col = Customer.age

    if order.lower() == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(asc(sort_col))

    total = query.count()
    offset = (page - 1) * page_size
    items_db = query.offset(offset).limit(page_size).all()

    items = []
    for c in items_db:
        cp = c.credit_profile
        cp_schema = CreditProfileSchema.model_validate(cp) if cp else None
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
            credit_profile=cp_schema
        ))

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/export/csv")
def export_customers_csv(
    risk_band: Optional[str] = None,
    education: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Export customer portfolio records to CSV format.
    """
    query = db.query(Customer).outerjoin(CreditProfile, Customer.customer_id == CreditProfile.customer_id)
    if risk_band:
        query = query.filter(CreditProfile.risk_band == risk_band)
    if education:
        query = query.filter(Customer.education_label == education)

    customers = query.limit(2000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Customer_ID", "Gender", "Education", "Marital_Status", "Age", "Age_Group",
        "Credit_Limit", "Risk_Score", "Risk_Band", "Utilization_Ratio", "Max_Delay_Months",
        "Repayment_Ratio", "Default_Next_Month", "Requires_Review", "Review_Status"
    ])

    for c in customers:
        cp = c.credit_profile
        writer.writerow([
            c.customer_id, c.sex_label, c.education_label, c.marriage_label, c.age, c.age_group,
            cp.limit_bal if cp else 0,
            cp.risk_score if cp else 0,
            cp.risk_band if cp else "N/A",
            cp.utilization_ratio if cp else 0,
            cp.max_delay_months if cp else 0,
            cp.repayment_ratio if cp else 0,
            cp.default_payment_next_month if cp else 0,
            cp.requires_manual_review if cp else False,
            cp.manual_review_status if cp else "N/A"
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers_portfolio.csv"}
    )

@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get customer demographic and credit profile.
    """
    cust = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    cp = cust.credit_profile
    return CustomerResponse(
        customer_id=cust.customer_id,
        sex=cust.sex,
        sex_label=cust.sex_label,
        education=cust.education,
        education_label=cust.education_label,
        marriage=cust.marriage,
        marriage_label=cust.marriage_label,
        age=cust.age,
        age_group=cust.age_group,
        created_at=cust.created_at,
        updated_at=cust.updated_at,
        credit_profile=CreditProfileSchema.model_validate(cp) if cp else None
    )

@router.get("/{customer_id}/details", response_model=CustomerDetailResponse)
def get_customer_details(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get complete customer record including 6 months of historical bills and repayments.
    """
    cust = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    cp = cust.credit_profile
    bills = [BillSchema.model_validate(b) for b in sorted(cust.bills, key=lambda x: x.month_idx)]
    payments = [PaymentSchema.model_validate(p) for p in sorted(cust.payments, key=lambda x: x.month_idx)]

    return CustomerDetailResponse(
        customer_id=cust.customer_id,
        sex=cust.sex,
        sex_label=cust.sex_label,
        education=cust.education,
        education_label=cust.education_label,
        marriage=cust.marriage,
        marriage_label=cust.marriage_label,
        age=cust.age,
        age_group=cust.age_group,
        created_at=cust.created_at,
        updated_at=cust.updated_at,
        credit_profile=CreditProfileSchema.model_validate(cp) if cp else None,
        bills=bills,
        payments=payments
    )

@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("administrator"))
):
    """
    Create a new customer account with credit profile. (Admin only)
    """
    if data.customer_id:
        existing = db.query(Customer).filter(Customer.customer_id == data.customer_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Customer with this ID already exists")
        cid = data.customer_id
    else:
        max_id = db.query(Customer.customer_id).order_by(desc(Customer.customer_id)).first()
        cid = (max_id[0] + 1) if max_id else 1

    cust = Customer(
        customer_id=cid,
        sex=data.sex,
        sex_label=decode_gender(data.sex),
        education=data.education,
        education_label=decode_education(data.education),
        marriage=data.marriage,
        marriage_label=decode_marriage(data.marriage),
        age=data.age,
        age_group=get_age_group(data.age)
    )
    db.add(cust)

    # Risk evaluation
    risk_res = risk_service.evaluate_risk(
        limit_bal=data.limit_bal,
        pay_statuses=[data.pay_status_0, 0, 0, 0, 0, 0],
        bill_amounts=[data.bill_amt_1, 0, 0, 0, 0, 0],
        pay_amounts=[data.pay_amt_1, 0, 0, 0, 0, 0]
    )

    profile = CreditProfile(
        customer_id=cid,
        limit_bal=data.limit_bal,
        default_payment_next_month=0,
        risk_score=risk_res["risk_score"],
        risk_band=risk_res["risk_band"],
        utilization_ratio=risk_res["utilization_ratio"],
        max_delay_months=risk_res["max_delay_months"],
        avg_bill_amt=risk_res["avg_bill_amt"],
        avg_pay_amt=risk_res["avg_pay_amt"],
        repayment_ratio=risk_res["repayment_ratio"],
        requires_manual_review=risk_res["requires_manual_review"],
        review_reasons=" | ".join(risk_res["review_reasons"])
    )
    db.add(profile)
    db.commit()
    db.refresh(cust)

    return CustomerResponse(
        customer_id=cust.customer_id,
        sex=cust.sex,
        sex_label=cust.sex_label,
        education=cust.education,
        education_label=cust.education_label,
        marriage=cust.marriage,
        marriage_label=cust.marriage_label,
        age=cust.age,
        age_group=cust.age_group,
        created_at=cust.created_at,
        updated_at=cust.updated_at,
        credit_profile=CreditProfileSchema.model_validate(profile)
    )

@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update customer demographic details.
    """
    cust = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    if data.sex is not None:
        cust.sex = data.sex
        cust.sex_label = decode_gender(data.sex)
    if data.education is not None:
        cust.education = data.education
        cust.education_label = decode_education(data.education)
    if data.marriage is not None:
        cust.marriage = data.marriage
        cust.marriage_label = decode_marriage(data.marriage)
    if data.age is not None:
        cust.age = data.age
        cust.age_group = get_age_group(data.age)

    db.commit()
    db.refresh(cust)
    return CustomerResponse(
        customer_id=cust.customer_id,
        sex=cust.sex,
        sex_label=cust.sex_label,
        education=cust.education,
        education_label=cust.education_label,
        marriage=cust.marriage,
        marriage_label=cust.marriage_label,
        age=cust.age,
        age_group=cust.age_group,
        created_at=cust.created_at,
        updated_at=cust.updated_at,
        credit_profile=CreditProfileSchema.model_validate(cust.credit_profile) if cust.credit_profile else None
    )

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("administrator"))
):
    """
    Delete customer and associated records. (Admin only)
    """
    cust = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    db.delete(cust)
    db.commit()
    return None

