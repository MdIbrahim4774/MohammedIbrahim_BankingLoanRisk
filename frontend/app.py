import os
import sys
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configure page
st.set_page_config(
    page_title="Banking Loan Risk Analysis Platform",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")

# Direct DB fallback helpers if FastAPI server is running in same process or local mode
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.core.config import settings
from src.core.database import SessionLocal, ACTIVE_DATABASE_URL
from src.models.db_models import (
    Customer, CreditProfile, Bill, Payment, DataQualityLog, ETLReconciliationLog, SegmentKPISummary
)
from src.services.risk_service import risk_service
from src.services.etl_service import etl_service
from src.core.security import SYSTEM_USERS, verify_password, create_access_token

# Custom CSS for styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #1E88E5;
    }
    .badge-high {
        background-color: #ffebee;
        color: #c62828;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-med {
        background-color: #fff8e1;
        color: #f57f17;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-low {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "token" not in st.session_state:
    st.session_state.token = None
if "role" not in st.session_state:
    st.session_state.role = None
if "username" not in st.session_state:
    st.session_state.username = None
if "full_name" not in st.session_state:
    st.session_state.full_name = None

def authenticate_user(username: str, password: str):
    """
    Authenticate against FastAPI REST endpoint with fallback to security module.
    """
    # 1. Try FastAPI REST API endpoint
    try:
        resp = requests.post(
            f"{API_BASE_URL}/auth/login",
            data={"username": username, "password": password},
            timeout=2
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "token": data["access_token"],
                "role": data["role"],
                "username": data["username"],
                "full_name": SYSTEM_USERS.get(data["username"], {}).get("full_name", data["username"].title())
            }
    except Exception:
        pass

    # 2. Local security check
    u = username.lower().strip()
    if u in SYSTEM_USERS and verify_password(password, SYSTEM_USERS[u]["password"]):
        user_info = SYSTEM_USERS[u]
        tok = create_access_token({"sub": u, "role": user_info["role"]})
        return {
            "token": tok,
            "role": user_info["role"],
            "username": u,
            "full_name": user_info["full_name"]
        }
    return None

# ==========================================
# 0. LOGIN PAGE (WHEN NOT AUTHENTICATED)
# ==========================================
if not st.session_state.authenticated:
    # Sidebar during unauthenticated state
    st.sidebar.image("https://img.icons8.com/color/96/bank-building.png", width=64)
    st.sidebar.title("Banking Risk Portal")
    st.sidebar.info(f"Database: **MySQL** (`{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}`)")
    st.sidebar.warning("🔒 Please sign in to access the system.")

    # Centered Login Card
    col_l1, col_l2, col_l3 = st.columns([1, 1.8, 1])
    with col_l2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://img.icons8.com/color/96/bank-building.png", width=80)
        st.title("Banking Risk Portal")
        st.markdown("##### Retail Loan Risk & Credit Exposure Analysis Platform")
        st.markdown("---")
        
        st.subheader("🔐 Secure Sign In")
        st.caption("Sign in with your assigned banking credentials to obtain a JWT session.")

        with st.form("login_form"):
            input_username = st.text_input("Username", placeholder="e.g. admin or analyst")
            input_password = st.text_input("Password", type="password", placeholder="••••••••")
            submit_login = st.form_submit_button("🚀 Sign In to Portal", use_container_width=True)

            if submit_login:
                if not input_username.strip() or not input_password.strip():
                    st.error("Please provide both username and password.")
                else:
                    auth_info = authenticate_user(input_username, input_password)
                    if auth_info:
                        st.session_state.authenticated = True
                        st.session_state.token = auth_info["token"]
                        st.session_state.role = auth_info["role"]
                        st.session_state.username = auth_info["username"]
                        st.session_state.full_name = auth_info["full_name"]
                        st.success(f"Welcome, {auth_info['full_name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please verify username and password.")

    st.stop()

# ==========================================
# SIDEBAR (AUTHENTICATED SESSION)
# ==========================================
st.sidebar.image("https://img.icons8.com/color/96/bank-building.png", width=64)
st.sidebar.title("Banking Risk Portal")
st.sidebar.caption("Credit Risk Monitoring & ETL System")

st.sidebar.markdown("---")
st.sidebar.success(f"👤 **{st.session_state.full_name}**")
st.sidebar.caption(f"Role: `{st.session_state.role.upper()}` &nbsp;|&nbsp; User: `{st.session_state.username}`")

if st.sidebar.button("🚪 Log Out", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.role = None
    st.session_state.username = None
    st.session_state.full_name = None
    st.rerun()

st.sidebar.info(f"Database Engine: **MySQL** (`{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}`)")
st.sidebar.markdown("---")
nav_choice = st.sidebar.radio(
    "Navigation Menu",
    [
        "📊 Portfolio KPI Dashboard",
        "👥 Customer Portfolio Explorer",
        "⚠️ Underwriter Review Queue",
        "📈 Demographic & Cashflow Trends",
        "🧪 Loan Risk & What-If Simulator",
        "⚙️ ETL & Data Quality Control",
        "🗄️ SQL Analytics Studio"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("Project 13: Banking Loan Risk Analysis Application")
st.sidebar.caption("FastAPI • MySQL • Pandas • Streamlit")


# ==========================================
# 1. PORTFOLIO KPI DASHBOARD
# ==========================================
if nav_choice == "📊 Portfolio KPI Dashboard":
    st.title("📊 Banking Portfolio Exposure & Risk Dashboard")
    st.write("Real-time monitoring of customer exposure, payment behaviors, and default distributions.")

    db = SessionLocal()
    try:
        total_cust = db.query(Customer).count()
        if total_cust == 0:
            st.warning("No records found in database. Please run the ETL Pipeline from the 'ETL & Data Quality Control' tab.")
        else:
            profiles = db.query(CreditProfile).all()
            df_prof = pd.DataFrame([{
                "limit_bal": p.limit_bal,
                "risk_score": p.risk_score,
                "risk_band": p.risk_band,
                "utilization_ratio": p.utilization_ratio,
                "repayment_ratio": p.repayment_ratio,
                "default": p.default_payment_next_month,
                "manual_review": p.requires_manual_review
            } for p in profiles])

            total_exp = df_prof["limit_bal"].sum()
            avg_limit = df_prof["limit_bal"].mean()
            default_rate = (df_prof["default"].mean()) * 100
            high_risk_pct = (df_prof["risk_band"] == "High").mean() * 100
            avg_util = df_prof["utilization_ratio"].mean() * 100
            pending_rev = df_prof["manual_review"].sum()

            # KPI Metric Row
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.metric("Total Customers", f"{total_cust:,}")
            k2.metric("Total Exposure", f"NT${total_exp/1e6:.1f}M")
            k3.metric("Avg Credit Limit", f"NT${avg_limit:,.0f}")
            k4.metric("Default Rate", f"{default_rate:.2f}%")
            k5.metric("High Risk Share", f"{high_risk_pct:.2f}%")
            k6.metric("Manual Review Flags", f"{pending_rev:,}")

            st.markdown("---")

            # Chart Row 1
            c1, c2, c3 = st.columns([1, 1, 1.2])

            with c1:
                st.subheader("Risk Band Breakdown")
                band_counts = df_prof["risk_band"].value_counts().reset_index()
                band_counts.columns = ["Risk Band", "Count"]
                color_map = {"Low": "#2e7d32", "Medium": "#f57f17", "High": "#c62828"}
                fig_bands = px.pie(
                    band_counts, names="Risk Band", values="Count",
                    color="Risk Band", color_discrete_map=color_map,
                    hole=0.45
                )
                fig_bands.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig_bands, use_container_width=True)

            with c2:
                st.subheader("Default Distribution")
                def_counts = df_prof["default"].map({0: "Non-Default (Good)", 1: "Default (30+ Days)"}).value_counts().reset_index()
                def_counts.columns = ["Status", "Count"]
                fig_def = px.bar(
                    def_counts, x="Status", y="Count", color="Status",
                    color_discrete_map={"Non-Default (Good)": "#1976D2", "Default (30+ Days)": "#E53935"}
                )
                fig_def.update_layout(margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
                st.plotly_chart(fig_def, use_container_width=True)

            with c3:
                st.subheader("Credit Limit vs Risk Score")
                fig_scatter = px.scatter(
                    df_prof.sample(min(500, len(df_prof))),
                    x="limit_bal", y="risk_score", color="risk_band",
                    color_discrete_map=color_map,
                    labels={"limit_bal": "Credit Limit (NTD)", "risk_score": "Risk Score (0-100)"},
                    hover_data=["utilization_ratio"]
                )
                fig_scatter.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig_scatter, use_container_width=True)

    finally:
        db.close()


# ==========================================
# 2. CUSTOMER PORTFOLIO EXPLORER
# ==========================================
elif nav_choice == "👥 Customer Portfolio Explorer":
    st.title("👥 Customer Portfolio Explorer & Credit Detail")
    st.write("Browse, search, and drill into individual customer statements, credit lines, and historical payments.")

    db = SessionLocal()
    try:
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            band_filter = st.selectbox("Risk Band:", ["All", "High", "Medium", "Low"])
        with col_f2:
            edu_filter = st.selectbox("Education:", ["All", "Graduate School", "University", "High School", "Others"])
        with col_f3:
            age_filter = st.selectbox("Age Group:", ["All", "20-29", "30-39", "40-49", "50-59", "60+"])
        with col_f4:
            search_id = st.text_input("Search Customer ID:", "")

        query = db.query(Customer).join(CreditProfile, Customer.customer_id == CreditProfile.customer_id)
        if band_filter != "All":
            query = query.filter(CreditProfile.risk_band == band_filter)
        if edu_filter != "All":
            query = query.filter(Customer.education_label == edu_filter)
        if age_filter != "All":
            query = query.filter(Customer.age_group == age_filter)
        if search_id.strip().isdigit():
            query = query.filter(Customer.customer_id == int(search_id.strip()))

        customers = query.limit(100).all()

        if not customers:
            st.info("No matching customer records found.")
        else:
            table_data = []
            for c in customers:
                cp = c.credit_profile
                table_data.append({
                    "Customer ID": c.customer_id,
                    "Gender": c.sex_label,
                    "Education": c.education_label,
                    "Marital": c.marriage_label,
                    "Age": c.age,
                    "Age Group": c.age_group,
                    "Credit Limit": f"NT${cp.limit_bal:,.0f}" if cp else "-",
                    "Risk Score": cp.risk_score if cp else 0,
                    "Risk Band": cp.risk_band if cp else "N/A",
                    "Utilization": f"{cp.utilization_ratio*100:.1f}%" if cp else "0%",
                    "Max Delay": f"{cp.max_delay_months} mo" if cp else "0 mo",
                    "Review Needed": "⚠️ YES" if cp and cp.requires_manual_review else "NO"
                })

            df_display = pd.DataFrame(table_data)
            st.dataframe(df_display, use_container_width=True, height=350)

            # Customer Drilldown Inspector
            st.markdown("---")
            st.subheader("🔍 Deep-Dive Customer Record Inspector")
            selected_cid = st.selectbox("Select Customer to Inspect:", [c.customer_id for c in customers])

            cust_obj = db.query(Customer).filter(Customer.customer_id == selected_cid).first()
            if cust_obj:
                prof = cust_obj.credit_profile
                col_d1, col_d2 = st.columns([1, 2])

                with col_d1:
                    st.markdown(f"### Account #{cust_obj.customer_id}")
                    st.write(f"**Demographics:** {cust_obj.age} yrs • {cust_obj.sex_label} • {cust_obj.marriage_label}")
                    st.write(f"**Education:** {cust_obj.education_label}")
                    st.write(f"**Credit Limit:** NT${prof.limit_bal:,.0f}")
                    st.write(f"**Risk Score:** {prof.risk_score:.1f} / 100")
                    st.write(f"**Risk Band:** {prof.risk_band}")
                    st.write(f"**Utilization Ratio:** {prof.utilization_ratio*100:.1f}%")
                    st.write(f"**Repayment Ratio:** {prof.repayment_ratio*100:.1f}%")
                    if prof.requires_manual_review:
                        st.error(f"⚠️ Flagged for Underwriter Review:\n{prof.review_reasons}")

                with col_d2:
                    st.markdown("### 6-Month Billing & Repayment Ledger")
                    bills = sorted(cust_obj.bills, key=lambda x: x.month_idx)
                    payments = sorted(cust_obj.payments, key=lambda x: x.month_idx)

                    ledger_data = []
                    for b, p in zip(bills, payments):
                        status_desc = "Paid duly" if p.pay_status <= 0 else f"{p.pay_status} mo delay"
                        ledger_data.append({
                            "Month": b.month_name,
                            "Billed Amount (NTD)": b.bill_amt,
                            "Payment (NTD)": p.pay_amt,
                            "Status": status_desc
                        })

                    df_ledger = pd.DataFrame(ledger_data)
                    st.table(df_ledger)

                    # Ledger chart
                    fig_ledger = go.Figure()
                    fig_ledger.add_trace(go.Bar(x=df_ledger["Month"], y=df_ledger["Billed Amount (NTD)"], name="Billed Amount", marker_color="#1E88E5"))
                    fig_ledger.add_trace(go.Bar(x=df_ledger["Month"], y=df_ledger["Payment (NTD)"], name="Paid Amount", marker_color="#43A047"))
                    fig_ledger.update_layout(barmode="group", height=250, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_ledger, use_container_width=True)

    finally:
        db.close()


# ==========================================
# 3. UNDERWRITER REVIEW QUEUE
# ==========================================
elif nav_choice == "⚠️ Underwriter Review Queue":
    st.title("⚠️ Credit Underwriter Manual Review Queue")
    st.write("Review accounts flagged by business rules (overleveraged limits, high delinquency, large exposure).")

    db = SessionLocal()
    try:
        status_filter = st.radio("Review Filter:", ["PENDING", "APPROVED", "REJECTED", "ALL"], horizontal=True)

        query = db.query(Customer).join(CreditProfile, Customer.customer_id == CreditProfile.customer_id).filter(
            CreditProfile.requires_manual_review == True
        )
        if status_filter != "ALL":
            query = query.filter(CreditProfile.manual_review_status == status_filter)

        flagged_customers = query.order_by(CreditProfile.risk_score.desc()).all()
        st.write(f"Total Flagged Accounts in Queue: **{len(flagged_customers)}**")

        if not flagged_customers:
            st.success("No accounts currently pending in this queue.")
        else:
            for c in flagged_customers[:15]:
                cp = c.credit_profile
                with st.expander(f"⚠️ Account #{c.customer_id} — Risk Score: {cp.risk_score:.1f} ({cp.risk_band}) — Status: {cp.manual_review_status}"):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.write(f"**Customer:** {c.age} yrs • {c.sex_label} • {c.education_label} • {c.marriage_label}")
                        st.write(f"**Exposure:** Credit Limit NT${cp.limit_bal:,.0f} | Utilization: {cp.utilization_ratio*100:.1f}%")
                        st.write(f"**Max Repayment Delay:** {cp.max_delay_months} months")
                        st.markdown(f"**Triggered Business Rules:**\n> {cp.review_reasons}")

                    with c2:
                        st.write(f"Current Status: **{cp.manual_review_status}**")
                        if cp.reviewed_by:
                            st.caption(f"Reviewed by: {cp.reviewed_by} at {cp.reviewed_at}")

                        u_notes = st.text_input("Underwriter Notes:", key=f"notes_{c.customer_id}")
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button("✅ Approve", key=f"app_{c.customer_id}"):
                                cp.manual_review_status = "APPROVED"
                                cp.reviewed_by = st.session_state.username
                                cp.reviewed_at = pd.Timestamp.now()
                                if u_notes:
                                    cp.review_reasons = (cp.review_reasons or "") + f" | Notes: {u_notes}"
                                db.commit()
                                st.success("Account Approved!")
                                st.rerun()
                        with btn_col2:
                            if st.button("❌ Reject", key=f"rej_{c.customer_id}"):
                                cp.manual_review_status = "REJECTED"
                                cp.reviewed_by = st.session_state.username
                                cp.reviewed_at = pd.Timestamp.now()
                                if u_notes:
                                    cp.review_reasons = (cp.review_reasons or "") + f" | Notes: {u_notes}"
                                db.commit()
                                st.error("Account Rejected!")
                                st.rerun()

    finally:
        db.close()


# ==========================================
# 4. DEMOGRAPHIC & CASHFLOW TRENDS
# ==========================================
elif nav_choice == "📈 Demographic & Cashflow Trends":
    st.title("📈 Demographic & Monthly Cashflow Analytics")
    st.write("Answering key portfolio questions regarding demographic risks and cashflow trends.")

    db = SessionLocal()
    try:
        summaries = db.query(SegmentKPISummary).all()
        if not summaries:
            st.warning("Pre-aggregated summaries empty. Run ETL to generate reporting tables.")
        else:
            df_sum = pd.DataFrame([{
                "type": s.segment_type,
                "value": s.segment_value,
                "count": s.customer_count,
                "limit": s.avg_limit_bal,
                "bill": s.avg_bill_amt,
                "pay": s.avg_pay_amt,
                "utilization": s.avg_utilization * 100,
                "default_rate": s.default_rate * 100,
                "high_risk_pct": s.high_risk_pct * 100
            } for s in summaries])

            t1, t2 = st.tabs(["👥 Demographic Risk Breakdown", "📅 Monthly Cashflow Trends"])

            with t1:
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.subheader("Default Rate by Education Level")
                    df_edu = df_sum[df_sum["type"] == "education"].sort_values("default_rate", ascending=False)
                    fig_edu = px.bar(df_edu, x="value", y="default_rate", color="value", text_auto=".1f",
                                     labels={"value": "Education", "default_rate": "Default Rate (%)"})
                    st.plotly_chart(fig_edu, use_container_width=True)

                with col_g2:
                    st.subheader("Default Rate & High Risk by Age Bracket")
                    df_age = df_sum[df_sum["type"] == "age_group"].sort_values("value")
                    fig_age = px.line(df_age, x="value", y=["default_rate", "high_risk_pct"], markers=True,
                                      labels={"value": "Age Bracket", "value": "Percentage (%)"})
                    st.plotly_chart(fig_age, use_container_width=True)

                st.subheader("Demographic KPI Summary Table")
                st.dataframe(df_sum[["type", "value", "count", "limit", "utilization", "default_rate", "high_risk_pct"]].rename(
                    columns={"type": "Segment", "value": "Category", "count": "Count", "limit": "Avg Limit", "utilization": "Avg Util %", "default_rate": "Default %", "high_risk_pct": "High Risk %"}
                ), use_container_width=True)

            with t2:
                st.subheader("6-Month Portfolio Cashflow Trends (April - September 2005)")
                # Query historical bills and payments
                trend_records = []
                for m_idx, m_name, _, _, _ in [
                    (6, "2005-04", "", "", ""), (5, "2005-05", "", "", ""),
                    (4, "2005-06", "", "", ""), (3, "2005-07", "", "", ""),
                    (2, "2005-08", "", "", ""), (1, "2005-09", "", "", "")
                ]:
                    b_tot = db.query(Bill.bill_amt).filter(Bill.month_idx == m_idx).all()
                    p_tot = db.query(Payment.pay_amt).filter(Payment.month_idx == m_idx).all()
                    delinq_cnt = db.query(Payment).filter(Payment.month_idx == m_idx, Payment.pay_status > 0).count()
                    tot_bills = len(b_tot)

                    b_sum = sum(x[0] for x in b_tot) if b_tot else 0.0
                    p_sum = sum(x[0] for x in p_tot) if p_tot else 0.0
                    trend_records.append({
                        "Month": m_name,
                        "Total Billed": b_sum,
                        "Total Repaid": p_sum,
                        "Net Expansion": b_sum - p_sum,
                        "Delinquency Rate (%)": round((delinq_cnt / tot_bills * 100), 2) if tot_bills > 0 else 0.0
                    })

                df_trends = pd.DataFrame(trend_records)

                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(x=df_trends["Month"], y=df_trends["Total Billed"], mode="lines+markers", name="Total Billed (NTD)", line=dict(color="#1E88E5", width=3)))
                fig_trend.add_trace(go.Scatter(x=df_trends["Month"], y=df_trends["Total Repaid"], mode="lines+markers", name="Total Repaid (NTD)", line=dict(color="#43A047", width=3)))
                st.plotly_chart(fig_trend, use_container_width=True)

                st.dataframe(df_trends, use_container_width=True)

    finally:
        db.close()


# ==========================================
# 5. LOAN RISK & WHAT-IF SIMULATOR
# ==========================================
elif nav_choice == "🧪 Loan Risk & What-If Simulator":
    st.title("🧪 Loan Risk Scoring & What-If Underwriting Simulator")
    st.write("Simulate underwriting decisions for new loan applicants or stress-test existing borrowing scenarios.")

    col_s1, col_s2 = st.columns([1, 1.2])

    with col_s1:
        st.subheader("Applicant Profile")
        sim_limit = st.number_input("Requested Credit Limit (NTD):", min_value=10000.0, max_value=1500000.0, value=200000.0, step=10000.0)
        sim_age = st.slider("Age:", min_value=18, max_value=80, value=32)
        sim_edu = st.selectbox("Education Level:", [1, 2, 3, 4], format_func=lambda x: {1: "Graduate School", 2: "University", 3: "High School", 4: "Others"}[x])
        sim_mar = st.selectbox("Marital Status:", [1, 2, 3], format_func=lambda x: {1: "Married", 2: "Single", 3: "Others"}[x])
        sim_sex = st.radio("Gender:", [1, 2], format_func=lambda x: "Male" if x == 1 else "Female", horizontal=True)

        st.subheader("Historical 6-Month Payment Status")
        st.caption("Status: -1=Duly paid, 0=Revolving, 1-8=Months delay")
        p0 = st.slider("Latest Month (Month 1):", -2, 8, 0)
        p2 = st.slider("Month 2:", -2, 8, 0)
        p3 = st.slider("Month 3:", -2, 8, 0)
        p4 = st.slider("Month 4:", -2, 8, 0)
        p5 = st.slider("Month 5:", -2, 8, 0)
        p6 = st.slider("Month 6:", -2, 8, 0)

        st.subheader("Recent Financial Activity")
        avg_monthly_bill = st.number_input("Average Monthly Bill Amount (NTD):", min_value=0.0, value=60000.0, step=5000.0)
        avg_monthly_pay = st.number_input("Average Monthly Payment (NTD):", min_value=0.0, value=40000.0, step=5000.0)

    with col_s2:
        st.subheader("Simulated Decision & Risk Output")
        
        sim_bills = [avg_monthly_bill] * 6
        sim_pays = [avg_monthly_pay] * 6
        sim_statuses = [p0, p2, p3, p4, p5, p6]

        res = risk_service.evaluate_risk(
            limit_bal=sim_limit,
            pay_statuses=sim_statuses,
            bill_amounts=sim_bills,
            pay_amounts=sim_pays
        )

        score = res["risk_score"]
        band = res["risk_band"]
        recom = res["approval_recommendation"]

        # Color banner
        if band == "Low":
            st.success(f"### Risk Band: LOW RISK\n**Recommendation:** {recom}")
        elif band == "Medium":
            st.warning(f"### Risk Band: MEDIUM RISK\n**Recommendation:** {recom}")
        else:
            st.error(f"### Risk Band: HIGH RISK\n**Recommendation:** {recom}")

        # Risk Gauge
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            title={'text': "Composite Risk Score (0-100)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#c62828" if score >= 65 else "#f57f17" if score >= 35 else "#2e7d32"},
                'steps': [
                    {'range': [0, 35], 'color': "#e8f5e9"},
                    {'range': [35, 65], 'color': "#fff8e1"},
                    {'range': [65, 100], 'color': "#ffebee"}
                ]
            }
        ))
        fig_gauge.update_layout(height=280, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

        st.write(f"**Utilization Ratio:** {res['utilization_ratio']*100:.1f}%")
        st.write(f"**Repayment Ratio:** {res['repayment_ratio']*100:.1f}%")
        st.write(f"**Maximum Recorded Delay:** {res['max_delay_months']} month(s)")

        if res["requires_manual_review"]:
            st.warning("⚠️ **Requires Additional Underwriter Review!**")
            for reason in res["review_reasons"]:
                st.write(f"• {reason}")
        else:
            st.info("✅ No business-rule exceptions detected.")


# ==========================================
# 6. ETL & DATA QUALITY CONTROL
# ==========================================
elif nav_choice == "⚙️ ETL & Data Quality Control":
    st.title("⚙️ ETL Pipeline & Data Batch Management")
    st.write(f"Automated batch pipeline: Place new data into `{settings.RAW_DATA_DIR}/`, process it into MySQL, and archive it into `{settings.PROCESSED_DATA_DIR}/`.")

    db = SessionLocal()
    try:
        # File status overview
        pending_files = etl_service.get_pending_raw_files()
        processed_files = etl_service.get_processed_files()

        st.markdown("### 📂 Data Pipeline Folders")
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.info(f"📥 **Pending Raw Batches (`{settings.RAW_DATA_DIR}/`):** {len(pending_files)} file(s)")
            if pending_files:
                for pf in pending_files:
                    st.code(f"• {pf}")
            else:
                st.caption("No pending raw files in `data/raw/`. Upload or drop a new dataset below.")

        with f_col2:
            st.success(f"📦 **Archived Processed Batches (`{settings.PROCESSED_DATA_DIR}/`):** {len(processed_files)} file(s)")
            if processed_files:
                for prf in processed_files[:5]:
                    st.code(f"• {prf}")
            else:
                st.caption("No archived processed files yet.")

        st.markdown("---")

        col_etl1, col_etl2 = st.columns([1.2, 1.5])

        with col_etl1:
            st.subheader("Process Raw Data Batch")
            
            # File uploader to add new batch to data/raw/
            uploaded_file = st.file_uploader("Upload New Data Batch to `data/raw/`:", type=["xls", "xlsx", "csv"])
            if uploaded_file is not None:
                save_dest = os.path.join(settings.RAW_DATA_DIR, uploaded_file.name)
                with open(save_dest, "wb") as f_out:
                    f_out.write(uploaded_file.getbuffer())
                st.success(f"Saved `{uploaded_file.name}` to `{settings.RAW_DATA_DIR}/`!")
                st.rerun()

            selected_raw = None
            if pending_files:
                selected_raw = st.selectbox("Select Raw File to Process:", pending_files)
            else:
                st.warning("No files found in `data/raw/`. Drop a file into `data/raw/` to trigger ETL.")

            custom_rows = st.number_input("Row limit (0 for entire file):", min_value=0, value=0, step=500)

            is_admin = (st.session_state.role == "administrator")
            run_disabled = (len(pending_files) == 0) or not is_admin
            if not is_admin:
                st.info("🔒 Administrator role required to trigger new ETL batches. Analysts have read-only access to audit logs.")

            if st.button("🚀 Process Batch & Move to Processed/", disabled=run_disabled, use_container_width=True):
                with st.spinner("Processing batch, running data quality checks, and archiving to data/processed/..."):
                    rows = custom_rows if custom_rows > 0 else None
                    try:
                        result = etl_service.run_pipeline(db=db, mode="batch", file_path=selected_raw, custom_rows=rows)
                        st.success(result["message"])
                        st.json(result)
                        st.rerun()
                    except Exception as e:
                        st.error(f"ETL Execution Failed: {str(e)}")

        with col_etl2:
            st.subheader("Record-Level Reconciliation Logs")
            recon_logs = db.query(ETLReconciliationLog).order_by(ETLReconciliationLog.created_at.desc()).limit(8).all()
            if recon_logs:
                df_recon = pd.DataFrame([{
                    "Batch ID": r.batch_id,
                    "Source Count": r.source_count,
                    "Loaded Count": r.loaded_count,
                    "Inserted": r.inserted_count,
                    "Updated": r.updated_count,
                    "Reconciled": "✅ YES" if r.reconciled else "❌ NO",
                    "Duration (s)": r.duration_sec,
                    "Timestamp": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
                } for r in recon_logs])
                st.dataframe(df_recon, use_container_width=True)
            else:
                st.info("No reconciliation logs recorded yet.")

        st.markdown("---")
        st.subheader("Data Quality Validation Results")
        dq_logs = db.query(DataQualityLog).order_by(DataQualityLog.created_at.desc()).limit(16).all()
        if dq_logs:
            df_dq = pd.DataFrame([{
                "Batch ID": d.batch_id,
                "Check Name": d.check_name,
                "Status": d.status,
                "Checked": d.records_checked,
                "Failed": d.failed_count,
                "Details": d.details,
                "Timestamp": d.created_at.strftime("%Y-%m-%d %H:%M:%S")
            } for d in dq_logs])
            st.dataframe(df_dq, use_container_width=True)
        else:
            st.info("No data quality checks recorded yet.")

    finally:
        db.close()


# ==========================================
# 7. SQL ANALYTICS STUDIO
# ==========================================
elif nav_choice == "🗄️ SQL Analytics Studio":
    st.title("🗄️ SQL Analytics & Ad-Hoc Business Studio")
    st.write("Execute production SQL queries answering loan exposure, repayment, and segment questions.")

    preset_queries = {
        "Overall Portfolio KPIs": """SELECT 
    COUNT(c.customer_id) AS total_customers,
    SUM(cp.limit_bal) AS total_credit_exposure,
    AVG(cp.limit_bal) AS avg_credit_limit,
    AVG(cp.utilization_ratio) AS avg_utilization_ratio,
    AVG(cp.default_payment_next_month) * 100 AS default_rate_pct,
    SUM(CASE WHEN cp.risk_band = 'High' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS high_risk_pct
FROM customers c
JOIN credit_profiles cp ON c.customer_id = cp.customer_id;""",

        "Education Segment Risk Analysis": """SELECT 
    c.education_label AS education_level,
    COUNT(c.customer_id) AS customer_count,
    ROUND(AVG(cp.limit_bal), 2) AS avg_credit_limit,
    ROUND(AVG(cp.utilization_ratio) * 100, 2) AS avg_utilization_pct,
    ROUND(AVG(cp.default_payment_next_month) * 100, 2) AS default_rate_pct,
    ROUND(SUM(CASE WHEN cp.risk_band = 'High' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS high_risk_share_pct
FROM customers c
JOIN credit_profiles cp ON c.customer_id = cp.customer_id
GROUP BY c.education_label
ORDER BY default_rate_pct DESC;""",

        "Age Group Delinquency Breakdown": """SELECT 
    c.age_group,
    COUNT(c.customer_id) AS customer_count,
    ROUND(AVG(cp.limit_bal), 2) AS avg_credit_limit,
    ROUND(AVG(cp.utilization_ratio) * 100, 2) AS avg_utilization_pct,
    ROUND(AVG(cp.default_payment_next_month) * 100, 2) AS default_rate_pct,
    ROUND(AVG(cp.risk_score), 2) AS avg_risk_score
FROM customers c
JOIN credit_profiles cp ON c.customer_id = cp.customer_id
GROUP BY c.age_group
ORDER BY c.age_group ASC;""",

        "Underwriter Review Exception Accounts": """SELECT 
    c.customer_id,
    c.age,
    c.education_label,
    cp.limit_bal,
    cp.risk_score,
    cp.risk_band,
    cp.utilization_ratio,
    cp.max_delay_months,
    cp.review_reasons
FROM customers c
JOIN credit_profiles cp ON c.customer_id = cp.customer_id
WHERE cp.requires_manual_review = 1
ORDER BY cp.risk_score DESC
LIMIT 50;"""
    }

    selected_preset = st.selectbox("Select Pre-configured Analytical Query:", list(preset_queries.keys()))
    query_text = st.text_area("SQL Statement:", preset_queries[selected_preset], height=180)

    if st.button("Execute SQL Query", type="primary"):
        db = SessionLocal()
        try:
            from sqlalchemy import text
            res = db.execute(text(query_text))
            rows = res.fetchall()
            cols = res.keys()
            df_sql = pd.DataFrame(rows, columns=cols)
            st.success(f"Query returned {len(df_sql)} rows.")
            st.dataframe(df_sql, use_container_width=True)

            csv_data = df_sql.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Results as CSV", csv_data, "query_results.csv", "text/csv")
        except Exception as e:
            st.error(f"SQL Execution Error: {str(e)}")
        finally:
            db.close()

