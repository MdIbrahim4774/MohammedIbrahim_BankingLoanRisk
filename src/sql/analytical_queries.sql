-- ====================================================================
-- Banking Loan Risk Analysis Application - Analytical SQL Queries
-- ====================================================================

-- 1. OVERALL EXPOSURE AND RISK KPIS
SELECT 
    COUNT(c.customer_id) AS total_customers,
    SUM(cp.limit_bal) AS total_credit_exposure,
    AVG(cp.limit_bal) AS avg_credit_limit,
    AVG(cp.utilization_ratio) AS avg_utilization_ratio,
    AVG(cp.repayment_ratio) AS avg_repayment_ratio,
    AVG(cp.default_payment_next_month) * 100 AS default_rate_pct,
    SUM(CASE WHEN cp.risk_band = 'High' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS high_risk_pct,
    SUM(CASE WHEN cp.requires_manual_review = 1 THEN 1 ELSE 0 END) AS manual_review_queue_count
FROM customers c
JOIN credit_profiles cp ON c.customer_id = cp.customer_id;


-- 2. DEMOGRAPHIC SEGMENT RISK & EXPOSURE (EDUCATION LEVEL)
-- Question: Which customer segments have higher payment-risk indicators?
SELECT 
    c.education_label AS education_level,
    COUNT(c.customer_id) AS customer_count,
    ROUND(AVG(cp.limit_bal), 2) AS avg_credit_limit,
    ROUND(AVG(cp.avg_bill_amt), 2) AS avg_monthly_bill,
    ROUND(AVG(cp.avg_pay_amt), 2) AS avg_monthly_payment,
    ROUND(AVG(cp.utilization_ratio) * 100, 2) AS avg_utilization_pct,
    ROUND(AVG(cp.default_payment_next_month) * 100, 2) AS default_rate_pct,
    ROUND(SUM(CASE WHEN cp.risk_band = 'High' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS high_risk_share_pct
FROM customers c
JOIN credit_profiles cp ON c.customer_id = cp.customer_id
GROUP BY c.education_label
ORDER BY default_rate_pct DESC;


-- 3. AGE GROUP EXPOSURE & DELINQUENCY ANALYSIS
-- Question: How do credit limits and payment behavior vary across customer age brackets?
SELECT 
    c.age_group,
    COUNT(c.customer_id) AS customer_count,
    ROUND(AVG(cp.limit_bal), 2) AS avg_credit_limit,
    ROUND(AVG(cp.utilization_ratio) * 100, 2) AS avg_utilization_pct,
    ROUND(AVG(cp.max_delay_months), 2) AS avg_max_delay_months,
    ROUND(AVG(cp.default_payment_next_month) * 100, 2) AS default_rate_pct,
    ROUND(AVG(cp.risk_score), 2) AS avg_risk_score
FROM customers c
JOIN credit_profiles cp ON c.customer_id = cp.customer_id
GROUP BY c.age_group
ORDER BY c.age_group ASC;


-- 4. MARITAL STATUS & GENDER RISK MATRIX
SELECT 
    c.sex_label AS gender,
    c.marriage_label AS marital_status,
    COUNT(c.customer_id) AS customer_count,
    ROUND(AVG(cp.limit_bal), 2) AS avg_credit_limit,
    ROUND(AVG(cp.utilization_ratio) * 100, 2) AS avg_utilization_pct,
    ROUND(AVG(cp.default_payment_next_month) * 100, 2) AS default_rate_pct
FROM customers c
JOIN credit_profiles cp ON c.customer_id = cp.customer_id
GROUP BY c.sex_label, c.marriage_label
ORDER BY default_rate_pct DESC;


-- 5. MONTHLY BILLING VS PAYMENT CASHFLOW TRENDS
-- Question: What are the monthly and segment-level trends in credit exposure and payment behavior?
SELECT 
    b.month_idx,
    b.month_name,
    ROUND(SUM(b.bill_amt), 2) AS total_billed_amount,
    ROUND(SUM(p.pay_amt), 2) AS total_repaid_amount,
    ROUND(SUM(b.bill_amt) - SUM(p.pay_amt), 2) AS net_credit_expansion,
    ROUND(SUM(p.pay_amt) / NULLIF(SUM(b.bill_amt), 0) * 100, 2) AS aggregate_collection_efficiency_pct,
    ROUND(AVG(CASE WHEN p.pay_status > 0 THEN 1.0 ELSE 0.0 END) * 100, 2) AS delinquency_rate_pct
FROM bills b
JOIN payments p ON b.customer_id = p.customer_id AND b.month_idx = p.month_idx
GROUP BY b.month_idx, b.month_name
ORDER BY b.month_idx ASC;


-- 6. RECORDS REQUIRING ADDITIONAL REVIEW BASED ON DEFINED BUSINESS RULES
-- Question: Which records require additional review based on defined business rules?
SELECT 
    c.customer_id,
    c.age,
    c.education_label,
    c.marriage_label,
    cp.limit_bal,
    cp.risk_score,
    cp.risk_band,
    cp.utilization_ratio,
    cp.max_delay_months,
    cp.review_reasons,
    cp.manual_review_status
FROM customers c
JOIN credit_profiles cp ON c.customer_id = cp.customer_id
WHERE cp.requires_manual_review = 1
ORDER BY cp.risk_score DESC, cp.limit_bal DESC
LIMIT 100;


-- 7. OVERLEVERAGED CUSTOMER IDENTIFICATION (HIGH UTILIZATION & HIGH DELINQUENCY)
SELECT 
    c.customer_id,
    c.age,
    c.education_label,
    cp.limit_bal,
    cp.avg_bill_amt,
    cp.utilization_ratio,
    cp.max_delay_months,
    cp.repayment_ratio,
    cp.default_payment_next_month
FROM customers c
JOIN credit_profiles cp ON c.customer_id = cp.customer_id
WHERE cp.utilization_ratio >= 0.85
  AND cp.max_delay_months >= 2
ORDER BY cp.utilization_ratio DESC, cp.limit_bal DESC;


-- 8. QUERY FROM PRE-AGGREGATED MATERIALIZED SUMMARY TABLE (OPTIMIZED DASHBOARD ACCELERATOR)
SELECT 
    segment_type,
    segment_value,
    customer_count,
    avg_limit_bal,
    avg_bill_amt,
    avg_pay_amt,
    avg_utilization,
    default_rate * 100 AS default_rate_pct,
    high_risk_pct * 100 AS high_risk_pct
FROM segment_kpi_summaries
ORDER BY segment_type, default_rate DESC;

