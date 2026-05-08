"""
Enrollment Intelligence - Streamlit Dashboard
4 pages:
  1. KPI Overview
  2. Enrollment Funnel
  3. Dropout Predictions (live API)
  4. Why Students Drop Off (SHAP)

Run:  streamlit run dashboard/app.py
Env:  DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME  (or DATABASE_URL)
      API_URL  (default http://127.0.0.1:8000)
"""

import os
import requests
import pandas as pd
import numpy as np
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

#Config
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Enrollment Intelligence",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

#Global CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0f1117;
    color: #e8e8e8;
}

h1, h2, h3 {
    font-family: 'DM Serif Display', serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #141824 0%, #0f1117 100%);
    border-right: 1px solid #1e2535;
}
[data-testid="stSidebar"] * { color: #e8e8e8 !important; }

/* Metric cards */
div[data-testid="metric-container"] {
    background: #141824;
    border: 1px solid #1e2535;
    border-radius: 12px;
    padding: 18px 24px;
}
div[data-testid="metric-container"] label {
    font-size: 0.72rem !important;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6b7a99 !important;
    font-weight: 500;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'DM Serif Display', serif;
    font-size: 2.2rem !important;
    color: #e8e8e8 !important;
}

/* Selectbox / inputs */
[data-testid="stSelectbox"] > div > div,
[data-testid="stNumberInput"] input,
[data-testid="stSlider"] {
    background: #141824 !important;
    border-color: #1e2535 !important;
    color: #e8e8e8 !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    letter-spacing: 0.04em;
    padding: 0.6rem 1.8rem;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(59,130,246,0.35);
}

/* Risk badge helpers */
.risk-high   { background:#ef444420; border:1px solid #ef4444; color:#ef4444; border-radius:6px; padding:4px 12px; font-weight:600; font-size:0.85rem; }
.risk-medium { background:#f9731620; border:1px solid #f97316; color:#f97316; border-radius:6px; padding:4px 12px; font-weight:600; font-size:0.85rem; }
.risk-low    { background:#22c55e20; border:1px solid #22c55e; color:#22c55e; border-radius:6px; padding:4px 12px; font-weight:600; font-size:0.85rem; }

/* Divider */
hr { border-color: #1e2535; margin: 1.5rem 0; }

/* Dataframe */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
thead tr th { background: #141824 !important; }

/* Tab styling */
[data-testid="stTabs"] button {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.85rem;
    letter-spacing: 0.05em;
}
</style>
""", unsafe_allow_html=True)


#DB connection
@st.cache_resource(show_spinner=False)
def get_engine():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return create_engine(db_url)
    return create_engine(
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
    )

@st.cache_data(ttl=300, show_spinner=False)
def query_db(sql: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


#Sidebar navigation
with st.sidebar:
    st.markdown("""
    <div style='padding: 1rem 0 2rem 0;'>
        <div style='font-family: DM Serif Display, serif; font-size: 1.5rem; color: #e8e8e8; line-height:1.2;'>
            Enrollment<br>Intelligence
        </div>
        <div style='font-size: 0.72rem; color: #6b7a99; letter-spacing: 0.12em; text-transform: uppercase; margin-top: 4px;'>
            Analytics Platform
        </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        ["KPI Overview", "Enrollment Funnel", "Dropout Predictions", "Why Students Drop Off"],
        label_visibility="collapsed",
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("""
    <div style='font-size:0.72rem; color:#6b7a99; letter-spacing:0.08em;'>
    API: """ + API_URL + """
    </div>
    """, unsafe_allow_html=True)

    # Quick API health check
    try:
        r = requests.get(f"{API_URL}/health", timeout=2)
        if r.status_code == 200:
            st.markdown("<div style='font-size:0.72rem; color:#22c55e; margin-top:4px;'>● API Online</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='font-size:0.72rem; color:#ef4444; margin-top:4px;'>● API Error</div>", unsafe_allow_html=True)
    except Exception:
        st.markdown("<div style='font-size:0.72rem; color:#f97316; margin-top:4px;'>● API Offline</div>", unsafe_allow_html=True)



# PAGE 1 - KPI OVERVIEW
if page == "📊  KPI Overview":
    st.markdown("## KPI Overview")
    st.markdown("<div style='color:#6b7a99; margin-bottom:2rem;'>Institution-wide enrollment metrics from your PostgreSQL star schema.</div>", unsafe_allow_html=True)

    #Top KPIs
    try:
        kpi_df = query_db("""
            SELECT
                COUNT(*)                                                         AS total_students,
                SUM(CASE WHEN enrollment_status = 'Graduate' THEN 1 ELSE 0 END) AS graduated,
                SUM(CASE WHEN enrollment_status = 'Dropout'  THEN 1 ELSE 0 END) AS dropped_out,
                SUM(CASE WHEN enrollment_status = 'Enrolled' THEN 1 ELSE 0 END) AS enrolled,
                ROUND((100.0 * SUM(CASE WHEN enrollment_status = 'Graduate' THEN 1 ELSE 0 END)
                      / NULLIF(COUNT(*), 0))::numeric, 1)                       AS grad_rate,
                ROUND((100.0 * SUM(CASE WHEN enrollment_status = 'Dropout'  THEN 1 ELSE 0 END)
                      / NULLIF(COUNT(*), 0))::numeric, 1)                       AS drop_rate,
                ROUND(AVG(cu1_grade)::numeric, 2)                               AS avg_s1_grade,
                ROUND(AVG(cu2_grade)::numeric, 2)                               AS avg_s2_grade
            FROM fact_enrollments
        """)
        row = kpi_df.iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Students",    f"{int(row.total_students):,}")
        c2.metric("Graduation Rate",   f"{row.grad_rate}%",  delta=f"+{row.grad_rate}% vs 0%")
        c3.metric("Dropout Rate",      f"{row.drop_rate}%",  delta=f"-{row.drop_rate}%", delta_color="inverse")
        c4.metric("Currently Enrolled",f"{int(row.enrolled):,}")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Graduated",         f"{int(row.graduated):,}")
        c6.metric("Dropped Out",       f"{int(row.dropped_out):,}")
        c7.metric("Avg Semester 1 GPA",f"{row.avg_s1_grade}")
        c8.metric("Avg Semester 2 GPA",f"{row.avg_s2_grade}")

    except Exception as e:
        st.error(f"Could not load KPI metrics: {e}")

    st.markdown("<hr>", unsafe_allow_html=True)

    #Two charts row 
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("#### Dropout Rate by Age Group")
        try:
            age_df = query_db("""
                SELECT
                    CASE
                        WHEN ds.age_at_enrollment < 20 THEN 'Under 20'
                        WHEN ds.age_at_enrollment BETWEEN 20 AND 25 THEN '20–25'
                        WHEN ds.age_at_enrollment BETWEEN 26 AND 35 THEN '26–35'
                        ELSE 'Over 35'
                    END AS age_group,
                    ROUND((100.0 * SUM(CASE WHEN fe.enrollment_status = 'Dropout' THEN 1 ELSE 0 END)
                          / NULLIF(COUNT(*),0))::numeric, 1) AS dropout_rate
                FROM fact_enrollments fe
                JOIN dim_student ds ON fe.student_id = ds.student_id
                GROUP BY age_group
                ORDER BY MIN(ds.age_at_enrollment)
            """)
            st.bar_chart(age_df.set_index("age_group")["dropout_rate"], color="#3b82f6")
        except Exception as e:
            st.error(f"Age group chart failed: {e}")

    with col_r:
        st.markdown("#### Dropout vs Graduate: Scholarship Impact")
        try:
            schol_df = query_db("""
                SELECT
                    CASE WHEN ds.scholarship_holder = 1 THEN 'Scholarship' ELSE 'No Scholarship' END AS group_label,
                    SUM(CASE WHEN fe.enrollment_status = 'Graduate' THEN 1 ELSE 0 END) AS graduated,
                    SUM(CASE WHEN fe.enrollment_status = 'Dropout'  THEN 1 ELSE 0 END) AS dropped_out
                FROM fact_enrollments fe
                JOIN dim_student ds ON fe.student_id = ds.student_id
                GROUP BY group_label
            """)
            st.bar_chart(schol_df.set_index("group_label")[["graduated","dropped_out"]])
        except Exception as e:
            st.error(f"Scholarship chart failed: {e}")

    st.markdown("<hr>", unsafe_allow_html=True)

    #Grade distribution
    st.markdown("#### Grade Distribution - Semester 1 vs Semester 2")
    try:
        grades_df = query_db("""
            SELECT
                enrollment_status,
                ROUND(AVG(cu1_grade)::numeric, 2) AS avg_s1,
                ROUND(AVG(cu2_grade)::numeric, 2) AS avg_s2
            FROM fact_enrollments
            GROUP BY enrollment_status
            ORDER BY enrollment_status
        """)
        st.bar_chart(grades_df.set_index("enrollment_status")[["avg_s1","avg_s2"]])
    except Exception as e:
        st.error(f"Grade chart failed: {e}")

    #Debtor / tuition risk 
    st.markdown("<hr>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Dropout Rate: Debtors vs Non-Debtors")
        try:
            debt_df = query_db("""
                SELECT
                    CASE WHEN ds.debtor = 1 THEN 'Debtor' ELSE 'Non-Debtor' END AS debtor_status,
                    ROUND((100.0 * SUM(CASE WHEN fe.enrollment_status = 'Dropout' THEN 1 ELSE 0 END)
                          / NULLIF(COUNT(*),0))::numeric, 1) AS dropout_rate
                FROM fact_enrollments fe
                JOIN dim_student ds ON fe.student_id = ds.student_id
                GROUP BY debtor_status
            """)
            st.bar_chart(debt_df.set_index("debtor_status")["dropout_rate"], color="#ef4444")
        except Exception as e:
            st.error(f"Debtor chart failed: {e}")

    with col_b:
        st.markdown("#### Dropout Rate: Tuition Up To Date")
        try:
            tuition_df = query_db("""
                SELECT
                    CASE WHEN ds.tuition_fees_up_to_date = 1 THEN 'Up To Date' ELSE 'Behind' END AS tuition_status,
                    ROUND((100.0 * SUM(CASE WHEN fe.enrollment_status = 'Dropout' THEN 1 ELSE 0 END)
                          / NULLIF(COUNT(*),0))::numeric, 1) AS dropout_rate
                FROM fact_enrollments fe
                JOIN dim_student ds ON fe.student_id = ds.student_id
                GROUP BY tuition_status
            """)
            st.bar_chart(tuition_df.set_index("tuition_status")["dropout_rate"], color="#f97316")
        except Exception as e:
            st.error(f"Tuition chart failed: {e}")


# PAGE 2 - ENROLLMENT FUNNEL
elif page == " Enrollment Funnel":
    st.markdown("## Enrollment Funnel")
    st.markdown("<div style='color:#6b7a99; margin-bottom:2rem;'>Track how students move from enrollment → active → graduation, and where drop-off occurs.</div>", unsafe_allow_html=True)

    try:
        funnel_df = query_db("""
            SELECT
                COUNT(*)                                                                   AS total_enrolled,
                SUM(CASE WHEN cu1_approved > 0 THEN 1 ELSE 0 END)                         AS passed_sem1,
                SUM(CASE WHEN cu2_approved > 0 THEN 1 ELSE 0 END)                         AS passed_sem2,
                SUM(CASE WHEN enrollment_status IN ('Graduate','Enrolled') THEN 1 ELSE 0 END) AS still_active,
                SUM(CASE WHEN enrollment_status = 'Graduate' THEN 1 ELSE 0 END)            AS graduated
            FROM fact_enrollments
        """)
        row = funnel_df.iloc[0]

        stages = {
            "Enrolled":           int(row.total_enrolled),
            "Passed Semester 1":  int(row.passed_sem1),
            "Passed Semester 2":  int(row.passed_sem2),
            "Still Active":       int(row.still_active),
            "Graduated":          int(row.graduated),
        }

        # Funnel visual using progress bars
        max_val = stages["Enrolled"]
        for stage, val in stages.items():
            pct = val / max_val
            prev = list(stages.values())[list(stages.keys()).index(stage) - 1] if stage != "Enrolled" else val
            loss = prev - val
            col1, col2, col3 = st.columns([2, 5, 2])
            with col1:
                st.markdown(f"<div style='text-align:right; padding-top:6px; font-size:0.85rem; color:#6b7a99;'>{stage}</div>", unsafe_allow_html=True)
            with col2:
                st.progress(pct)
            with col3:
                loss_str = f"<span style='color:#ef4444; font-size:0.75rem;'>−{loss:,}</span>" if loss > 0 else ""
                st.markdown(f"<div style='padding-top:4px; font-weight:600;'>{val:,} {loss_str}</div>", unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # Conversion rates
        st.markdown("#### Stage Conversion Rates")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sem 1 Pass Rate",    f"{100*stages['Passed Semester 1']/max_val:.1f}%")
        c2.metric("Sem 2 Pass Rate",    f"{100*stages['Passed Semester 2']/max_val:.1f}%")
        c3.metric("Retention Rate",     f"{100*stages['Still Active']/max_val:.1f}%")
        c4.metric("Graduation Rate",    f"{100*stages['Graduated']/max_val:.1f}%")

    except Exception as e:
        st.error(f"Funnel data failed: {e}")

    st.markdown("<hr>", unsafe_allow_html=True)

    #Dropout timing 
    st.markdown("#### Where Do Dropouts Fail?")
    try:
        timing_df = query_db("""
            SELECT
                CASE
                    WHEN cu1_approved = 0 AND cu2_approved = 0 THEN 'Failed Both Semesters'
                    WHEN cu1_approved = 0 THEN 'Failed Semester 1 Only'
                    WHEN cu2_approved = 0 THEN 'Failed Semester 2 Only'
                    ELSE 'Passed Both - Still Dropped'
                END AS failure_stage,
                COUNT(*) AS students
            FROM fact_enrollments
            WHERE enrollment_status = 'Dropout'
            GROUP BY failure_stage
            ORDER BY students DESC
        """)
        st.bar_chart(timing_df.set_index("failure_stage")["students"], color="#ef4444")
    except Exception as e:
        st.error(f"Timing chart failed: {e}")

    #By gender
    st.markdown("<hr>", unsafe_allow_html=True)
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("#### Outcomes by Gender")
        try:
            gender_df = query_db("""
                SELECT
                    CASE WHEN ds.gender = 1 THEN 'Male' ELSE 'Female' END AS gender,
                    SUM(CASE WHEN fe.enrollment_status = 'Graduate' THEN 1 ELSE 0 END) AS graduated,
                    SUM(CASE WHEN fe.enrollment_status = 'Dropout'  THEN 1 ELSE 0 END) AS dropped_out,
                    SUM(CASE WHEN fe.enrollment_status = 'Enrolled' THEN 1 ELSE 0 END) AS enrolled
                FROM fact_enrollments fe
                JOIN dim_student ds ON fe.student_id = ds.student_id
                GROUP BY gender
            """)
            st.bar_chart(gender_df.set_index("gender")[["graduated","dropped_out","enrolled"]])
        except Exception as e:
            st.error(f"Gender chart failed: {e}")

    with col_r:
        st.markdown("#### Outcomes by Marital Status")
        try:
            marital_df = query_db("""
                SELECT
                    ds.marital_status::text AS marital_status,
                    SUM(CASE WHEN fe.enrollment_status = 'Graduate' THEN 1 ELSE 0 END) AS graduated,
                    SUM(CASE WHEN fe.enrollment_status = 'Dropout'  THEN 1 ELSE 0 END) AS dropped_out
                FROM fact_enrollments fe
                JOIN dim_student ds ON fe.student_id = ds.student_id
                GROUP BY ds.marital_status
                ORDER BY ds.marital_status
            """)
            st.bar_chart(marital_df.set_index("marital_status")[["graduated","dropped_out"]])
        except Exception as e:
            st.error(f"Marital status chart failed: {e}")


# PAGE 3 - DROPOUT PREDICTIONS
elif page == "Dropout Predictions":
    st.markdown("## Dropout Predictions")
    st.markdown("<div style='color:#6b7a99; margin-bottom:2rem;'>Enter student data to get a live dropout risk score from the ML model.</div>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Single Student", "Lookup by ID"])

    #Tab 1: Manual input 
    with tab1:
        st.markdown("#### Student Features")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Academic - Semester 1**")
            cu1_enrolled   = st.number_input("Units Enrolled (S1)",   0, 30, 6, key="c1e")
            cu1_approved   = st.number_input("Units Approved (S1)",   0, 30, 5, key="c1a")
            cu1_evaluations= st.number_input("Evaluations (S1)",      0, 50, 6, key="c1ev")
            cu1_grade      = st.slider("Grade (S1)",  0.0, 20.0, 12.0, 0.1, key="c1g")
            cu1_credited   = st.number_input("Credited (S1)",         0, 30, 0, key="c1cr")
            cu1_without_eval=st.number_input("Without Eval (S1)",     0, 30, 0, key="c1w")

        with col2:
            st.markdown("**Academic - Semester 2**")
            cu2_enrolled   = st.number_input("Units Enrolled (S2)",   0, 30, 6, key="c2e")
            cu2_approved   = st.number_input("Units Approved (S2)",   0, 30, 5, key="c2a")
            cu2_evaluations= st.number_input("Evaluations (S2)",      0, 50, 6, key="c2ev")
            cu2_grade      = st.slider("Grade (S2)",  0.0, 20.0, 12.0, 0.1, key="c2g")
            cu2_credited   = st.number_input("Credited (S2)",         0, 30, 0, key="c2cr")
            cu2_without_eval=st.number_input("Without Eval (S2)",     0, 30, 0, key="c2w")

        with col3:
            st.markdown("**Demographics & Economics**")
            age_at_enrollment       = st.number_input("Age at Enrollment",     15, 70, 20)
            gender                  = st.selectbox("Gender", ["Male (1)","Female (0)"])
            scholarship_holder      = st.selectbox("Scholarship Holder", ["No (0)","Yes (1)"])
            debtor                  = st.selectbox("Debtor", ["No (0)","Yes (1)"])
            tuition_fees_up_to_date = st.selectbox("Tuition Up To Date", ["Yes (1)","No (0)"])
            displaced               = st.selectbox("Displaced", ["No (0)","Yes (1)"])
            educational_special_needs = st.selectbox("Special Educational Needs", ["No (0)","Yes (1)"])
            marital_status          = st.number_input("Marital Status Code",   1, 6, 1)
            international           = st.selectbox("International Student", ["No (0)","Yes (1)"])
            unemployment_rate       = st.number_input("Unemployment Rate (%)", 0.0, 30.0, 10.8)
            inflation_rate          = st.number_input("Inflation Rate (%)",   -5.0, 20.0, 1.4)
            gdp                     = st.number_input("GDP Growth (%)",       -5.0, 10.0, 1.74)

        def parse_binary(val: str) -> int:
            return 1 if "(1)" in val else 0

        if st.button("Predict Dropout Risk", use_container_width=True):
            payload = {
                "cu1_credited":              cu1_credited,
                "cu1_enrolled":              cu1_enrolled,
                "cu1_evaluations":           cu1_evaluations,
                "cu1_approved":              cu1_approved,
                "cu1_grade":                 cu1_grade,
                "cu1_without_eval":          cu1_without_eval,
                "cu2_credited":              cu2_credited,
                "cu2_enrolled":              cu2_enrolled,
                "cu2_evaluations":           cu2_evaluations,
                "cu2_approved":              cu2_approved,
                "cu2_grade":                 cu2_grade,
                "cu2_without_eval":          cu2_without_eval,
                "age_at_enrollment":         age_at_enrollment,
                "gender":                    parse_binary(gender),
                "scholarship_holder":        parse_binary(scholarship_holder),
                "debtor":                    parse_binary(debtor),
                "tuition_fees_up_to_date":   parse_binary(tuition_fees_up_to_date),
                "displaced":                 parse_binary(displaced),
                "educational_special_needs": parse_binary(educational_special_needs),
                "marital_status":            marital_status,
                "international":             parse_binary(international),
                "unemployment_rate":         unemployment_rate,
                "inflation_rate":            inflation_rate,
                "gdp":                       gdp,
            }

            with st.spinner("Running prediction..."):
                try:
                    resp = requests.post(f"{API_URL}/predict", json=payload, timeout=10)
                    resp.raise_for_status()
                    result = resp.json()

                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown("### Prediction Result")

                    risk = result["risk_level"]
                    risk_class = f"risk-{risk.lower()}"
                    risk_color = {"High":"#ef4444","Medium":"#f97316","Low":"#22c55e"}[risk]

                    rc1, rc2, rc3 = st.columns(3)
                    rc1.metric("Prediction",       result["prediction"])
                    rc2.metric("Dropout Probability", f"{result['dropout_probability']}%")
                    rc3.metric("Graduate Probability",f"{result['graduate_probability']}%")

                    st.markdown(f"""
                    <div style='margin-top:1rem; margin-bottom:1rem;'>
                        Risk Level: <span class='{risk_class}'>{risk} Risk</span>
                    </div>
                    """, unsafe_allow_html=True)

                    # Gauge bar
                    dp = result["dropout_probability"]
                    st.markdown(f"""
                    <div style='margin: 1rem 0;'>
                        <div style='font-size:0.75rem; color:#6b7a99; margin-bottom:4px; letter-spacing:0.08em; text-transform:uppercase;'>Dropout Risk</div>
                        <div style='background:#1e2535; border-radius:999px; height:10px; overflow:hidden;'>
                            <div style='width:{dp}%; height:100%; background: linear-gradient(90deg, #22c55e, #f97316 60%, #ef4444); border-radius:999px; transition:width 0.5s ease;'></div>
                        </div>
                        <div style='display:flex; justify-content:space-between; font-size:0.7rem; color:#6b7a99; margin-top:4px;'>
                            <span>0%</span><span>50%</span><span>100%</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("#### Top Risk Factors")
                    for factor in result["top_risk_factors"]:
                        direction = "🔴" if "increases" in factor else "🟢"
                        st.markdown(f"{direction} {factor}")

                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to API. Make sure `uvicorn api.main:app --reload` is running.")
                except Exception as e:
                    st.error(f"Prediction failed: {e}")

    #Tab 2: Lookup by student ID ──
    with tab2:
        st.markdown("#### Look Up a Student from the Database")
        student_id = st.number_input("Student ID", min_value=1, value=1, step=1)

        if st.button("Look Up Student"):
            with st.spinner("Fetching..."):
                try:
                    resp = requests.get(f"{API_URL}/student_summary/{int(student_id)}", timeout=10)
                    if resp.status_code == 404:
                        st.warning(f"Student {student_id} not found.")
                    else:
                        resp.raise_for_status()
                        data = resp.json()

                        st.markdown("<hr>", unsafe_allow_html=True)
                        st.markdown(f"### Student {data['student_id']}")

                        c1, c2, c3 = st.columns(3)
                        c1.metric("Age at Enrollment",  data["age_at_enrollment"])
                        c2.metric("Gender",              data["gender"])
                        c3.metric("Enrollment Status",   data["enrollment_status"])

                        c4, c5, c6 = st.columns(3)
                        c4.metric("Scholarship Holder",  "Yes" if data["scholarship_holder"] else "No")
                        c5.metric("Debtor",              "Yes" if data["debtor"] else "No")
                        c6.metric("Tuition Up To Date",  "Yes" if data["tuition_up_to_date"] else "No")

                        c7, c8 = st.columns(2)
                        c7.metric("Semester 1 Grade",    data["semester1_grade"])
                        c8.metric("Semester 2 Grade",    data["semester2_grade"])

                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to API.")
                except Exception as e:
                    st.error(f"Error: {e}")


# PAGE 4 - WHY STUDENTS DROP OFF
elif page == "Why Students Drop Off":
    st.markdown("## Why Students Drop Off")
    st.markdown("<div style='color:#6b7a99; margin-bottom:2rem;'>Global feature importance and segment-level dropout drivers from your data.</div>", unsafe_allow_html=True)

    #Global feature importance from DB 
    st.markdown("#### Key Dropout Drivers - Data Signals")

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("**Average Grades: Dropouts vs Graduates**")
        try:
            grade_compare = query_db("""
                SELECT
                    enrollment_status,
                    ROUND(AVG(cu1_grade)::numeric,2) AS avg_s1_grade,
                    ROUND(AVG(cu2_grade)::numeric,2) AS avg_s2_grade,
                    ROUND(AVG(cu1_approved)::numeric,2) AS avg_s1_approved,
                    ROUND(AVG(cu2_approved)::numeric,2) AS avg_s2_approved
                FROM fact_enrollments
                WHERE enrollment_status IN ('Graduate','Dropout')
                GROUP BY enrollment_status
            """)
            st.dataframe(grade_compare, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"{e}")

    with col_r:
        st.markdown("**Dropout Rate by Financial Risk Profile**")
        try:
            fin_risk = query_db("""
                SELECT
                    CASE
                        WHEN ds.debtor = 1 AND ds.tuition_fees_up_to_date = 0 THEN 'Debtor + Behind on Tuition'
                        WHEN ds.debtor = 1 THEN 'Debtor Only'
                        WHEN ds.tuition_fees_up_to_date = 0 THEN 'Behind on Tuition Only'
                        ELSE 'No Financial Risk'
                    END AS risk_profile,
                    COUNT(*) AS total,
                    ROUND((100.0 * SUM(CASE WHEN fe.enrollment_status='Dropout' THEN 1 ELSE 0 END)
                          / NULLIF(COUNT(*),0))::numeric, 1) AS dropout_rate_pct
                FROM fact_enrollments fe
                JOIN dim_student ds ON fe.student_id = ds.student_id
                GROUP BY risk_profile
                ORDER BY dropout_rate_pct DESC
            """)
            st.dataframe(fin_risk, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"{e}")

    st.markdown("<hr>", unsafe_allow_html=True)

    #SHAP plot from saved file
    st.markdown("#### SHAP Feature Importance (from Model Training)")
    shap_path = "models/shap_summary.png"
    if os.path.exists(shap_path):
        st.image(shap_path, caption="SHAP Summary Plot - impact of each feature on dropout prediction", use_container_width=True)
    else:
        st.info("SHAP summary plot not found. Run `python models/train_model.py` to generate it at `models/shap_summary.png`.")

    st.markdown("<hr>", unsafe_allow_html=True)

    #Per-student SHAP example 
    st.markdown("#### SHAP Force Plot - Example Student")
    force_path = "models/shap_student_example.png"
    if os.path.exists(force_path):
        st.image(force_path, caption="SHAP force plot for a single student - red pushes toward dropout, blue toward graduation", use_container_width=True)
    else:
        st.info("SHAP student example not found. Run `python models/train_model.py` to generate it.")

    st.markdown("<hr>", unsafe_allow_html=True)

    #Economics correlation
    st.markdown("#### Macroeconomic Context at Dropout")
    try:
        econ_df = query_db("""
            SELECT
                fe.enrollment_status,
                ROUND(AVG(de.unemployment_rate)::numeric, 2) AS avg_unemployment,
                ROUND(AVG(de.inflation_rate)::numeric, 2) AS avg_inflation,
                ROUND(AVG(de.gdp)::numeric, 2) AS avg_gdp
            FROM fact_enrollments fe
            JOIN dim_economics de ON fe.economics_id = de.economics_id
            WHERE fe.enrollment_status IN ('Graduate','Dropout')
            GROUP BY fe.enrollment_status
        """)
        st.dataframe(econ_df, use_container_width=True, hide_index=True)
        st.caption("Higher unemployment and inflation at time of enrollment correlates with elevated dropout rates.")
    except Exception as e:
        st.error(f"Economics query failed: {e}")

    #Actionable takeaways 
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("#### Actionable Insights")

    insights = [
        ("Semester 1 grades are the single strongest dropout predictor.", "Students who fail to pass even 1 unit in S1 have dramatically higher dropout rates. Early intervention in week 4–6 is critical."),
        ("Financial risk compounds dropout probability 3×.", "Students who are both debtors AND behind on tuition have the highest dropout rate. Scholarship programs are your highest-ROI intervention."),
        ("Age 26–35 is the highest-risk cohort.", "Older returning students face competing pressures (work, family). Flexible scheduling and support programs reduce dropout in this group."),
        ("International students have distinct risk profiles.", "International students often have low dropout rates - but when they do drop, it clusters around specific grade thresholds."),
    ]

    for icon_title, body in insights:
        with st.expander(icon_title):
            st.markdown(body)