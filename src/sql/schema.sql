-- ====================================================================
-- Banking Loan Risk Analysis Application - MySQL Relational Schema
-- Database: loan_risk_db
-- ====================================================================

CREATE DATABASE IF NOT EXISTS loan_risk_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE loan_risk_db;

-- 1. Customers Table (Demographics)
CREATE TABLE IF NOT EXISTS customers (
    customer_id INT NOT NULL,
    sex TINYINT NOT NULL COMMENT '1=Male, 2=Female',
    sex_label VARCHAR(20) NULL,
    education TINYINT NOT NULL COMMENT '1=Grad School, 2=Univ, 3=High School, 4=Others',
    education_label VARCHAR(50) NULL,
    marriage TINYINT NOT NULL COMMENT '1=Married, 2=Single, 3=Others',
    marriage_label VARCHAR(30) NULL,
    age INT NOT NULL,
    age_group VARCHAR(20) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_id),
    INDEX idx_cust_age_group (age_group),
    INDEX idx_cust_demographics (age_group, education_label, marriage_label)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Credit Profiles Table (Financial Exposure, Risk Scoring & Audit Flags)
CREATE TABLE IF NOT EXISTS credit_profiles (
    profile_id INT AUTO_INCREMENT,
    customer_id INT NOT NULL UNIQUE,
    limit_bal DECIMAL(12, 2) NOT NULL,
    default_payment_next_month TINYINT NOT NULL DEFAULT 0,
    risk_score DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
    risk_band VARCHAR(20) NOT NULL COMMENT 'Low, Medium, High',
    utilization_ratio DECIMAL(6, 4) NOT NULL DEFAULT 0.0000,
    max_delay_months INT NOT NULL DEFAULT 0,
    avg_bill_amt DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    avg_pay_amt DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    repayment_ratio DECIMAL(6, 4) NOT NULL DEFAULT 0.0000,
    requires_manual_review BOOLEAN NOT NULL DEFAULT FALSE,
    review_reasons TEXT NULL,
    manual_review_status VARCHAR(30) NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING, APPROVED, REJECTED',
    reviewed_by VARCHAR(100) NULL,
    reviewed_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (profile_id),
    CONSTRAINT fk_credit_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    INDEX idx_risk_band (risk_band),
    INDEX idx_manual_review (requires_manual_review, manual_review_status),
    INDEX idx_risk_score (risk_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Bills Table (Monthly Statement Balances)
CREATE TABLE IF NOT EXISTS bills (
    bill_id INT AUTO_INCREMENT,
    customer_id INT NOT NULL,
    month_idx TINYINT NOT NULL COMMENT '1=Sept, 2=Aug, 3=Jul, 4=Jun, 5=May, 6=Apr',
    month_name VARCHAR(20) NOT NULL,
    bill_amt DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (bill_id),
    CONSTRAINT fk_bill_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    INDEX idx_bill_cust_month (customer_id, month_idx),
    INDEX idx_bill_month (month_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Payments Table (Historical Monthly Repayments & Delay Status)
CREATE TABLE IF NOT EXISTS payments (
    payment_id INT AUTO_INCREMENT,
    customer_id INT NOT NULL,
    month_idx TINYINT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    pay_amt DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    pay_status INT NOT NULL DEFAULT 0 COMMENT '-2=No consumption, -1=Paid duly, 0=Revolving, 1-8=Months delay',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (payment_id),
    CONSTRAINT fk_payment_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    INDEX idx_payment_cust_month (customer_id, month_idx),
    INDEX idx_payment_status (pay_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Data Quality Audit Logs
CREATE TABLE IF NOT EXISTS data_quality_logs (
    log_id INT AUTO_INCREMENT,
    batch_id VARCHAR(50) NOT NULL,
    check_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    records_checked INT NOT NULL DEFAULT 0,
    failed_count INT NOT NULL DEFAULT 0,
    details TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (log_id),
    INDEX idx_dq_batch (batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. ETL Reconciliation Logs
CREATE TABLE IF NOT EXISTS etl_reconciliation_logs (
    recon_id INT AUTO_INCREMENT,
    batch_id VARCHAR(50) NOT NULL,
    source_count INT NOT NULL,
    loaded_count INT NOT NULL,
    reconciled BOOLEAN NOT NULL DEFAULT FALSE,
    source_checksum VARCHAR(64) NULL,
    loaded_checksum VARCHAR(64) NULL,
    inserted_count INT NOT NULL DEFAULT 0,
    updated_count INT NOT NULL DEFAULT 0,
    duration_sec DECIMAL(8, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(30) NOT NULL DEFAULT 'SUCCESS',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (recon_id),
    INDEX idx_recon_batch (batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Pre-aggregated Reporting Summary Table (Indexed KPI Accelerators)
CREATE TABLE IF NOT EXISTS segment_kpi_summaries (
    summary_id INT AUTO_INCREMENT,
    segment_type VARCHAR(50) NOT NULL,
    segment_value VARCHAR(50) NOT NULL,
    customer_count INT NOT NULL,
    avg_limit_bal DECIMAL(12, 2) NOT NULL,
    avg_bill_amt DECIMAL(12, 2) NOT NULL,
    avg_pay_amt DECIMAL(12, 2) NOT NULL,
    avg_utilization DECIMAL(6, 4) NOT NULL,
    default_rate DECIMAL(6, 4) NOT NULL,
    high_risk_pct DECIMAL(6, 4) NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (summary_id),
    INDEX idx_seg_summary (segment_type, segment_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

