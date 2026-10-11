from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

# Authentication Schemas
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    username: str
    role: str
    full_name: str

# Bill & Payment Schemas
class BillSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    bill_id: Optional[int] = None
    customer_id: int
    month_idx: int
    month_name: str
    bill_amt: float

class PaymentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    payment_id: Optional[int] = None
    customer_id: int
    month_idx: int
    month_name: str
    pay_amt: float
    pay_status: int

# Credit Profile Schemas
class CreditProfileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    profile_id: Optional[int] = None
    customer_id: int
    limit_bal: float
    default_payment_next_month: int
    risk_score: float
    risk_band: str
    utilization_ratio: float
    max_delay_months: int
    avg_bill_amt: float
    avg_pay_amt: float
    repayment_ratio: float
    requires_manual_review: bool
    review_reasons: Optional[str] = None
    manual_review_status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

class CreditProfileUpdate(BaseModel):
    limit_bal: Optional[float] = None
    manual_review_status: Optional[str] = None
    reviewed_by: Optional[str] = None

# Customer Schemas
class CustomerBase(BaseModel):
    sex: int = Field(..., ge=1, le=2, description="1=Male, 2=Female")
    education: int = Field(..., ge=0, le=6, description="1=Grad, 2=Univ, 3=High School, 4=Others")
    marriage: int = Field(..., ge=0, le=3, description="1=Married, 2=Single, 3=Others")
    age: int = Field(..., ge=18, le=100)

class CustomerCreate(CustomerBase):
    customer_id: Optional[int] = None
    limit_bal: float = Field(..., gt=0)
    pay_status_0: int = 0
    bill_amt_1: float = 0.0
    pay_amt_1: float = 0.0

class CustomerUpdate(BaseModel):
    sex: Optional[int] = None
    education: Optional[int] = None
    marriage: Optional[int] = None
    age: Optional[int] = None

class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    customer_id: int
    sex_label: Optional[str] = None
    education_label: Optional[str] = None
    marriage_label: Optional[str] = None
    age_group: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    credit_profile: Optional[CreditProfileSchema] = None

class CustomerDetailResponse(CustomerResponse):
    bills: List[BillSchema] = []
    payments: List[PaymentSchema] = []

# Risk Evaluation Schema
class RiskEvaluationRequest(BaseModel):
    customer_id: Optional[int] = None
    limit_bal: float = Field(..., gt=0)
    age: int = Field(..., ge=18, le=100)
    education: int = Field(..., ge=0, le=6)
    marriage: int = Field(..., ge=0, le=3)
    sex: int = Field(..., ge=1, le=2)
    pay_statuses: List[int] = Field(..., description="6 months of repayment statuses [PAY_0..PAY_6]")
    bill_amounts: List[float] = Field(..., description="6 months of bill amounts [BILL_AMT1..BILL_AMT6]")
    pay_amounts: List[float] = Field(..., description="6 months of payment amounts [PAY_AMT1..PAY_AMT6]")

class RiskEvaluationResponse(BaseModel):
    risk_score: float
    risk_band: str  # 'Low', 'Medium', 'High'
    utilization_ratio: float
    max_delay_months: int
    repayment_ratio: float
    requires_manual_review: bool
    review_reasons: List[str]
    rule_triggers: Dict[str, Any]
    approval_recommendation: str

# KPI & Analytical Schemas
class OverallKPIs(BaseModel):
    total_customers: int
    total_credit_exposure: float
    avg_credit_limit: float
    overall_default_rate: float
    high_risk_customers_pct: float
    avg_utilization_ratio: float
    avg_repayment_ratio: float
    pending_manual_reviews: int

class SegmentKPIItem(BaseModel):
    segment_type: str
    segment_value: str
    customer_count: int
    avg_limit_bal: float
    avg_bill_amt: float
    avg_pay_amt: float
    avg_utilization: float
    default_rate: float
    high_risk_pct: float

class MonthlyTrendItem(BaseModel):
    month_idx: int
    month_name: str
    total_bill_amount: float
    total_pay_amount: float
    avg_bill_amount: float
    avg_pay_amount: float
    delinquent_rate: float

# ETL and Quality Schemas
class ETLRunRequest(BaseModel):
    mode: str = Field("batch", description="'batch' or 'custom'")
    file_path: Optional[str] = Field(None, description="Optional specific file name in data/raw/ or path")
    custom_rows: Optional[int] = Field(None, description="Optional row limit to process")

class ETLRunResponse(BaseModel):
    batch_id: str
    mode: str
    source_file: Optional[str] = None
    processed_file_path: Optional[str] = None
    source_count: int
    loaded_count: int
    reconciled: bool
    duration_sec: float
    remaining_raw_batches: int = 0
    message: str

class ReconciliationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    recon_id: int
    batch_id: str
    source_count: int
    loaded_count: int
    reconciled: bool
    source_checksum: Optional[str] = None
    loaded_checksum: Optional[str] = None
    inserted_count: int
    updated_count: int
    duration_sec: float
    status: str
    created_at: datetime

class DataQualityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    log_id: int
    batch_id: str
    check_name: str
    status: str
    records_checked: int
    failed_count: int
    details: Optional[str] = None
    created_at: datetime

# Generic Paginated Wrapper
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int

