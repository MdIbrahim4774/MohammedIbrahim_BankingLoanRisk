from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index, Text
)
from sqlalchemy.orm import relationship
from src.core.database import Base

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(Integer, primary_key=True, index=True)
    sex = Column(Integer, nullable=False)                  # 1=Male, 2=Female
    sex_label = Column(String(20), nullable=True)          # 'Male', 'Female'
    education = Column(Integer, nullable=False)            # 1=Grad, 2=Univ, 3=High School, 4=Others
    education_label = Column(String(50), nullable=True)    # 'Graduate School', 'University', etc.
    marriage = Column(Integer, nullable=False)             # 1=Married, 2=Single, 3=Others
    marriage_label = Column(String(30), nullable=True)     # 'Married', 'Single', 'Others'
    age = Column(Integer, nullable=False, index=True)
    age_group = Column(String(20), nullable=False, index=True) # '20-29', '30-39', etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    credit_profile = relationship("CreditProfile", back_populates="customer", uselist=False, cascade="all, delete-orphan")
    bills = relationship("Bill", back_populates="customer", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="customer", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_customer_demographics", "age_group", "education_label", "marriage_label"),
    )


class CreditProfile(Base):
    __tablename__ = "credit_profiles"

    profile_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), unique=True, nullable=False, index=True)
    limit_bal = Column(Float, nullable=False)
    default_payment_next_month = Column(Integer, nullable=False, default=0, index=True) # 0 or 1
    
    # Computed Risk Indicators
    risk_score = Column(Float, nullable=False, default=0.0, index=True)
    risk_band = Column(String(20), nullable=False, index=True)  # 'Low', 'Medium', 'High'
    utilization_ratio = Column(Float, nullable=False, default=0.0) # avg bill / limit
    max_delay_months = Column(Integer, nullable=False, default=0, index=True)
    avg_bill_amt = Column(Float, nullable=False, default=0.0)
    avg_pay_amt = Column(Float, nullable=False, default=0.0)
    repayment_ratio = Column(Float, nullable=False, default=0.0)
    
    # Business Rules & Workflow Review
    requires_manual_review = Column(Boolean, nullable=False, default=False, index=True)
    review_reasons = Column(Text, nullable=True)
    manual_review_status = Column(String(30), nullable=False, default="PENDING") # PENDING, APPROVED, REJECTED
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="credit_profile")

    __table_args__ = (
        Index("idx_credit_risk_band", "risk_band", "requires_manual_review"),
    )


class Bill(Base):
    __tablename__ = "bills"

    bill_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False, index=True)
    month_idx = Column(Integer, nullable=False)   # 1=Sept 2005, 2=Aug 2005, ... 6=April 2005
    month_name = Column(String(20), nullable=False) # '2005-09', '2005-08', etc.
    bill_amt = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="bills")

    __table_args__ = (
        Index("idx_bill_customer_month", "customer_id", "month_idx"),
    )


class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False, index=True)
    month_idx = Column(Integer, nullable=False)   # 1=Sept, ... 6=April
    month_name = Column(String(20), nullable=False)
    pay_amt = Column(Float, nullable=False, default=0.0)
    pay_status = Column(Integer, nullable=False, default=0) # -2=no consumption, -1=duly, 0=revolving, 1-8=months delay
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="payments")

    __table_args__ = (
        Index("idx_payment_customer_month", "customer_id", "month_idx"),
    )


class DataQualityLog(Base):
    __tablename__ = "data_quality_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(50), nullable=False, index=True)
    check_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # PASS, WARNING, FAIL
    records_checked = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ETLReconciliationLog(Base):
    __tablename__ = "etl_reconciliation_logs"

    recon_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(50), nullable=False, index=True)
    source_count = Column(Integer, nullable=False)
    loaded_count = Column(Integer, nullable=False)
    reconciled = Column(Boolean, nullable=False, default=False)
    source_checksum = Column(String(64), nullable=True)
    loaded_checksum = Column(String(64), nullable=True)
    inserted_count = Column(Integer, nullable=False, default=0)
    updated_count = Column(Integer, nullable=False, default=0)
    duration_sec = Column(Float, nullable=False, default=0.0)
    status = Column(String(30), nullable=False, default="SUCCESS")
    created_at = Column(DateTime, default=datetime.utcnow)


class SegmentKPISummary(Base):
    __tablename__ = "segment_kpi_summaries"

    summary_id = Column(Integer, primary_key=True, autoincrement=True)
    segment_type = Column(String(50), nullable=False, index=True) # 'education', 'age_group', 'marriage', 'gender'
    segment_value = Column(String(50), nullable=False, index=True)
    customer_count = Column(Integer, nullable=False)
    avg_limit_bal = Column(Float, nullable=False)
    avg_bill_amt = Column(Float, nullable=False)
    avg_pay_amt = Column(Float, nullable=False)
    avg_utilization = Column(Float, nullable=False)
    default_rate = Column(Float, nullable=False)
    high_risk_pct = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

