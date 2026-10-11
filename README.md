# Banking Loan Risk Analysis Application (Project 13)

[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.143-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.65-FF4B4B.svg)](https://streamlit.io/)
[![MySQL](https://img.shields.io/badge/MySQL-Compatible-4479A1.svg)](https://www.mysql.com/)
[![Tests Passing](https://img.shields.io/badge/Tests-14%2F14%20Passed-brightgreen.svg)]()

A full-stack banking analysis and credit risk management application that performs automated ETL, stores curated customer data in a relational database, provides explainable rule-based risk band classifications (Low, Medium, High), triggers underwriter manual review workflows, exposes high-performance REST APIs with Role-Based Access Control (RBAC), and serves an interactive Streamlit analytics portal.

---

## 1. Project Overview

Banks and financial institutions manage large portfolios of credit lines and retail loan accounts. Credit risk analysts and loan underwriters require automated, transparent, and auditable systems to import customer statements, validate data quality, calculate financial exposure ratios, track multi-month repayment delinquency, and generate executive risk reports.

This microservice replaces manual, error-prone spreadsheet processes with an automated Python, FastAPI, MySQL, Pandas, and Streamlit architecture that provides real-time portfolio visibility and transparent underwriter decision support.

---

## 2. Key Business Questions Solved

* **Which customer segments have higher payment-risk indicators?**
  * Identified elevated default rates and high-risk shares across High School education levels (26.2% default rate) and senior age brackets (60+ at 28.6% default rate).
* **How do credit limits, payment history, bills, and previous payments vary across customers?**
  * Evaluated average credit lines, credit utilization ratios, and multi-cycle cash recovery efficiencies across demographics.
* **Which records require additional review based on defined business rules?**
  * Automated rule-based flagging for overleveraged accounts, high credit exposure with delinquency, chronic payment distress, and large balances with zero repayment.
* **What are the monthly and segment-level trends in credit exposure and payment behavior?**
  * Tracked 6 months of historical billing versus cash repayments, delinquency trends, and net portfolio credit expansion.

---

## 3. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Programming Language** | Python 3.14+ | Core data processing and business logic |
| **Relational Database** | MySQL (via PyMySQL & SQLAlchemy) | 3NF normalized tables, ACID transactions, and indexes |
| **Backend REST API** | FastAPI / Uvicorn | Asynchronous ASGI microservice, OpenAPI docs, Pydantic V2 |
| **Data Processing & ETL** | Pandas, SQLAlchemy ORM, openpyxl, xlrd | Vector transformations, cleaning, and upserts |
| **Frontend UI Dashboard** | Streamlit, Plotly Express | Interactive KPI dashboard, underwriter queue, and simulator |
| **Security & RBAC** | PyJWT, Cryptography, OAuth2 | Role-based access control (Analyst vs Administrator) |
| **Testing & Quality** | Pytest | 14 automated unit, integration, and API tests |
| **Job Scheduling** | APScheduler | Background periodic batch ETL processing |

---

## 4. System Architecture

The application is structured into decoupled, enterprise-grade layers:

```
UCI Credit Card Dataset (30,000 records)
             │
             ▼
┌────────────────────────────────────────────────────────┐
│ 1. ETL Pipeline & Data Quality Auditor                │
│    - Extraction: Excel (.xls/.xlsx) & CSV (.csv)       │
│    - 8 Data Quality Audits (Ranges, Domain, Anomaly)   │
│    - Cryptographic MD5 Record Reconciliation           │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ 2. Relational Storage Layer (MySQL)                    │
│    - customers: Demographics, decoded labels, age group│
│    - credit_profiles: Limits, risk score, band, ratios │
│    - bills: 6-month historical billing statements      │
│    - payments: 6-month historical repayment ledger     │
│    - segment_kpi_summaries: Pre-aggregated accelerators│
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ 3. Risk & Business Rules Engine                        │
│    - Multi-factor credit scoring (0 to 100)            │
│    - Low / Medium / High Risk Bands                    │
│    - Automated Manual Underwriter Review Flagging      │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ 4. FastAPI REST API Layer (Uvicorn ASGI Microservice)  │
│    - /auth: JWT RBAC (Analyst vs Administrator)        │
│    - /customers: Paginated CRUD, Search, Filter, Export│
│    - /risk: Underwriter Review Queue & Scoring API     │
│    - /analytics: Portfolio KPIs, Segments & Trends     │
│    - /etl: Pipeline execution & audit logs             │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ 5. Streamlit Interactive Web Portal                    │
│    - Executive Portfolio KPIs & Risk Donut Breakdown   │
│    - Customer Explorer & 6-Month Ledger Drilldown      │
│    - Underwriter Decisioning Queue (Approve / Reject)  │
│    - Demographic & Cashflow Trends (Plotly)           │
│    - Real-Time Loan Risk & What-If Simulator           │
│    - ETL & Data Quality Control Center                 │
│    - SQL Analytics Studio                              │
└────────────────────────────────────────────────────────┘
```

---

## 5. Relational Database Schema

### Relational Tables:
1. `customers`: Primary demographics (`customer_id`, `sex`, `sex_label`, `education`, `education_label`, `marriage`, `marriage_label`, `age`, `age_group`, timestamps).
2. `credit_profiles`: Financial exposure and risk classification (`profile_id`, `customer_id`, `limit_bal`, `default_payment_next_month`, `risk_score`, `risk_band`, `utilization_ratio`, `max_delay_months`, `avg_bill_amt`, `avg_pay_amt`, `repayment_ratio`, `requires_manual_review`, `review_reasons`, `manual_review_status`, `reviewed_by`, `reviewed_at`).
3. `bills`: Monthly statement balances (`bill_id`, `customer_id`, `month_idx`, `month_name`, `bill_amt`).
4. `payments`: Monthly cash repayments and delay status (`payment_id`, `customer_id`, `month_idx`, `month_name`, `pay_amt`, `pay_status`).
5. `data_quality_logs`: Audit logs for duplicate, range, and categorical sanity checks.
6. `etl_reconciliation_logs`: Cryptographic source vs target count and MD5 checksum reconciliation logs.
7. `segment_kpi_summaries`: Pre-aggregated summary tables indexed for sub-millisecond dashboard KPI responses.

Full MySQL DDL script is located in [`src/sql/schema.sql`](file:///home/ibrahim/Final%20Project/src/sql/schema.sql).

---

## 6. Business Rules & Risk Band Thresholds

### Documented Risk Bands:
* **High Risk (Score ≥ 65):**
  * Maximum repayment delay $\ge 2$ months, OR
  * Credit utilization ratio $\ge 85\%$ accompanied by repayment ratio $< 20\%$, OR
  * Known historical default indicator (`default_payment_next_month == 1`).
* **Medium Risk (Score 35 to 64):**
  * Maximum repayment delay $= 1$ month, OR
  * Credit utilization ratio between $60\%$ and $85\%$, OR
  * Repayment ratio between $20\%$ and $50\%$.
* **Low Risk (Score < 35):**
  * Maximum repayment delay $\le 0$ months, AND
  * Credit utilization ratio $< 60\%$, AND
  * Repayment ratio $\ge 50\%$.

### Configurable Manual Underwriter Review Triggers:
* **Rule 1 - High Exposure Delinquency:** Credit limit $> \text{NT}\$500,000$ with any payment delay ($\ge 1$ month).
* **Rule 2 - Overleveraged Low Repayment:** Credit utilization $> 90\%$ with repayment ratio $< 15\%$.
* **Rule 3 - Chronic Payment Distress:** Delinquency recorded across 2 or more distinct billing cycles with maximum delay $\ge 2$.
* **Rule 4 - High Statement Zero Repayment:** Outstanding statement balance $\ge \text{NT}\$50,000$ with zero recent cash payment.

---

## 7. Installation & Setup Instructions

### Prerequisites
* Python 3.10+ (tested on Python 3.14)
* MySQL Server 8.0+

### Step 1: Clone the Repository and Navigate to Root
```bash
git clone <repository_url>
cd "Final Project"
```

### Step 2: Set Up Virtual Environment & Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure MySQL Database & .env
1. **Initialize the MySQL Database and Schema:**
   Log into your MySQL server and run the provided schema script:
   ```bash
   mysql -u root -p < src/sql/schema.sql
   ```
   *(This creates the `loan_risk_db` database and all 7 relational tables with optimal indexes).*

2. **Configure your `.env` file:**
   Copy `.env.example` to `.env` (or edit `.env`):
   ```env
   # MySQL Database Configuration
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=your_mysql_password
   MYSQL_DB=loan_risk_db

   # Optional direct connection string override:
   # DATABASE_URL=mysql+pymysql://root:your_mysql_password@localhost:3306/loan_risk_db?charset=utf8mb4
   ```

3. **Run the Initial ETL to Populate MySQL:**
   ```bash
   python -c "from src.core.database import SessionLocal; from src.services.etl_service import etl_service; db = SessionLocal(); etl_service.run_pipeline(db=db, mode='full'); db.close()"
   ```

---

## 8. Running the Application

### 1. Launch the FastAPI Microservice Backend
```bash
# Using uvicorn command
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Or using the launcher script
python src/main.py
```
* **API Service:** http://127.0.0.1:8000
* **Interactive OpenAPI Swagger Docs:** http://127.0.0.1:8000/docs
* **ReDoc Documentation:** http://127.0.0.1:8000/redoc

### 2. Launch the Streamlit Frontend Dashboard
In a separate terminal:
```bash
streamlit run frontend/app.py

# Or via the root launcher
streamlit run frontend.py
```
* **Streamlit Portal:** http://localhost:8501

### Default Demo Credentials:
* **Administrator:** `username: admin` | `password: admin123`
* **Credit Analyst:** `username: analyst` | `password: analyst123`

---

## 9. Sample API Requests and Responses

### 1. User Authentication (JWT Token)
**Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=analyst&password=analyst123"
```
**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "analyst",
  "username": "analyst"
}
```

### 2. Real-Time Risk Evaluation & What-If Simulation
**Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/risk/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "limit_bal": 200000.0,
    "age": 35,
    "education": 1,
    "marriage": 2,
    "sex": 1,
    "pay_statuses": [0, 0, 0, 0, 0, 0],
    "bill_amounts": [30000, 30000, 30000, 30000, 30000, 30000],
    "pay_amounts": [30000, 30000, 30000, 30000, 30000, 30000]
  }'
```
**Response:**
```json
{
  "risk_score": 15.0,
  "risk_band": "Low",
  "utilization_ratio": 0.15,
  "max_delay_months": 0,
  "repayment_ratio": 1.0,
  "requires_manual_review": false,
  "review_reasons": [],
  "rule_triggers": {
    "high_exposure_delinquency": false,
    "extreme_utilization_low_repayment": false,
    "chronic_delinquency": false,
    "large_balance_zero_repayment": false
  },
  "approval_recommendation": "STANDARD_APPROVAL"
}
```

### 3. Portfolio KPIs Summary
**Request:**
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/analytics/kpis" \
  -H "Authorization: Bearer <TOKEN>"
```
**Response:**
```json
{
  "total_customers": 3000,
  "total_credit_exposure": 505700000.0,
  "avg_credit_limit": 168566.67,
  "overall_default_rate": 21.87,
  "high_risk_customers_pct": 39.83,
  "avg_utilization_ratio": 0.4285,
  "avg_repayment_ratio": 0.5892,
  "pending_manual_reviews": 772
}
```

### 4. Fetch Underwriter Manual Review Queue
**Request:**
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/risk/review-queue?page=1&page_size=2&review_status=PENDING" \
  -H "Authorization: Bearer <TOKEN>"
```
**Response:**
```json
{
  "items": [
    {
      "customer_id": 452,
      "sex": 2,
      "sex_label": "Female",
      "education": 2,
      "education_label": "University",
      "marriage": 1,
      "marriage_label": "Married",
      "age": 42,
      "age_group": "40-49",
      "credit_profile": {
        "limit_bal": 500000.0,
        "risk_score": 88.5,
        "risk_band": "High",
        "requires_manual_review": true,
        "review_reasons": "High credit limit exposure (NT$500,000) with 2-month payment delay",
        "manual_review_status": "PENDING"
      }
    }
  ],
  "total": 772,
  "page": 1,
  "page_size": 2,
  "total_pages": 386
}
```

---

## 10. Running Automated Tests

Run the complete test suite with verbose reporting:
```bash
pytest tests/ -v
```

### Test Suite Summary:
* `tests/test_api.py`: 5 tests (Health check, Auth login, Customer list/filter, Risk evaluation, Portfolio KPIs).
* `tests/test_business_rules.py`: 3 tests (Low-risk thresholding, High-risk delinquency scoring, Manual review triggers).
* `tests/test_data_quality_and_reconciliation.py`: 2 tests (Data quality rule validation, Checksum generation).
* `tests/test_etl.py`: 2 tests (Categorical decoding, Sample ETL pipeline execution).
* `tests/test_sql_and_db.py`: 2 tests (Relational CRUD operations, Pre-aggregated segment summary tables).
* **Result: 14 passed in 1.44s (100% pass rate).**

---

## 11. Project Folder Structure & Deliverables

```
Final Project/
├── architecture/
│   ├── Architecture_Diagram.pdf       # High-resolution PDF Architecture Diagram
│   └── Architecture_Diagram.png       # PNG Architecture Diagram
├── design/
│   └── Design_Document.pdf            # Comprehensive System Design Document
├── docs/
│   ├── API_Documentation.pdf          # REST API Specification & Endpoints
│   ├── Dataset_Details.pdf            # Dataset Dictionary, Ranges & Preprocessing
│   └── Evaluation_Report.pdf          # Technical Benchmarks, Tests & Insights
├── presentation/
│   └── Project_Presentation.pptx      # 10-Slide Panel Presentation Deck
├── data/
│   ├── raw/                           # Incoming raw data batches awaiting ETL (.xls, .xlsx, .csv)
│   └── processed/                     # Archived batches moved automatically after successful ETL
├── src/
│   ├── api/
│   │   ├── routers/
│   │   │   ├── auth.py                # JWT Authentication & RBAC
│   │   │   ├── customers.py           # CRUD, Pagination, Filter & CSV Export
│   │   │   ├── risk_analysis.py       # Scoring Engine & Review Queue Workflow
│   │   │   ├── analytics.py           # Portfolio KPIs, Segments & Trends
│   │   │   └── etl.py                 # Pipeline Trigger & Audit Logs
│   │   └── main.py                    # FastAPI Application Instance & Lifespan
│   ├── core/
│   │   ├── config.py                  # Pydantic Settings & Configurable Rules
│   │   ├── database.py                # MySQL Engine, SessionLocal & Pooling
│   │   └── security.py                # Password Hashing, JWT & Roles
│   ├── models/
│   │   ├── db_models.py               # SQLAlchemy Relational Models & Indexes
│   │   └── schemas.py                 # Pydantic Request/Response Schemas
│   ├── services/
│   │   ├── etl_service.py             # Ingestion, Cleaning, Upsert & Summary Tables
│   │   ├── risk_service.py            # Risk Scoring, Bands & Rule Triggers
│   │   ├── data_quality_service.py    # 8 Reusable Data Quality Audits
│   │   └── reconciliation_service.py  # MD5 Checksum & Count Reconciliation
│   ├── sql/
│   │   ├── schema.sql                 # Production MySQL Relational DDL
│   │   └── analytical_queries.sql     # 8 Business Analytical SQL Queries
│   ├── utils/
│   │   ├── logger.py                  # Structured Rotating Logger
│   │   └── scheduler.py               # Background Batch Job Scheduler
│   └── main.py                        # API Launcher Script
├── frontend/
│   └── app.py                         # Multi-Tab Interactive Streamlit Portal
├── frontend.py                        # Root Streamlit Launcher
├── tests/                             # 14 Automated Pytest Test Cases
├── requirements.txt                   # Complete Python Dependencies
├── pytest.ini                         # Test Configuration
└── README.md                          # Full Project Documentation
```

---

## 12. Submission Checklist Verification

* [x] Complete executable source code (FastAPI, MySQL, Pandas, Streamlit)
* [x] `architecture/Architecture_Diagram.pdf` and `Architecture_Diagram.png`
* [x] `design/Design_Document.pdf`
* [x] `docs/API_Documentation.pdf`
* [x] `docs/Dataset_Details.pdf`
* [x] `docs/Evaluation_Report.pdf`
* [x] `presentation/Project_Presentation.pptx`
* [x] Automated batch data pipeline (`data/raw/` to `data/processed/`)
* [x] Working REST APIs with JWT role-based access
* [x] Automated tests (14/14 passed)
* [x] Local deployment instructions and README documentation
* [x] No hardcoded secrets or API keys committed

