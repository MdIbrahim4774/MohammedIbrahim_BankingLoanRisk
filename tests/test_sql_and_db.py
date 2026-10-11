from tests.conftest import requires_mysql

@requires_mysql
def test_database_crud_operations():
    init_db()
    db = SessionLocal()
    try:
        # Create
        cust = Customer(
            customer_id=999999,
            sex=1,
            sex_label="Male",
            education=1,
            education_label="Graduate School",
            marriage=2,
            marriage_label="Single",
            age=29,
            age_group="20-29"
        )
        db.add(cust)
        
        profile = CreditProfile(
            customer_id=999999,
            limit_bal=250000.0,
            default_payment_next_month=0,
            risk_score=25.0,
            risk_band="Low",
            utilization_ratio=0.15,
            max_delay_months=0,
            avg_bill_amt=37500.0,
            avg_pay_amt=37500.0,
            repayment_ratio=1.0,
            requires_manual_review=False
        )
        db.add(profile)
        db.commit()

        # Read
        fetched = db.query(Customer).filter(Customer.customer_id == 999999).first()
        assert fetched is not None
        assert fetched.credit_profile.limit_bal == 250000.0

        # Update
        fetched.age = 30
        fetched.age_group = "30-39"
        db.commit()
        db.refresh(fetched)
        assert fetched.age == 30
        assert fetched.age_group == "30-39"

        # Delete
        db.delete(fetched)
        db.commit()
        deleted = db.query(Customer).filter(Customer.customer_id == 999999).first()
        assert deleted is None
    finally:
        db.close()

@requires_mysql
def test_segment_kpi_summaries():
    db = SessionLocal()
    try:
        summaries = db.query(SegmentKPISummary).all()
        assert len(summaries) > 0
    finally:
        db.close()

