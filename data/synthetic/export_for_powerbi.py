import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

os.makedirs("data/powerbi_exports", exist_ok=True)

queries = {
    "fact_enrollments": "SELECT * FROM fact_enrollments",
    "dim_student":      "SELECT * FROM dim_student",
    "dim_economics":    "SELECT * FROM dim_economics",
    "dim_course":       "SELECT * FROM dim_course",
    "financial_aid":    "SELECT * FROM financial_aid",
    "applications":     "SELECT * FROM applications",
    "validation_report":"SELECT * FROM validation_report",
    "kpi_summary": """
        SELECT
            COUNT(*) AS total_students,
            SUM(CASE WHEN enrollment_status = 'Graduate' THEN 1 ELSE 0 END) AS graduated,
            SUM(CASE WHEN enrollment_status = 'Dropout'  THEN 1 ELSE 0 END) AS dropped_out,
            SUM(CASE WHEN enrollment_status = 'Enrolled' THEN 1 ELSE 0 END) AS currently_enrolled,
            ROUND((100.0 * SUM(CASE WHEN enrollment_status = 'Graduate' THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0))::numeric, 2) AS graduation_rate_pct,
            ROUND((100.0 * SUM(CASE WHEN enrollment_status = 'Dropout' THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0))::numeric, 2) AS dropout_rate_pct,
            ROUND(AVG(cu1_grade)::numeric, 2) AS avg_semester1_grade,
            ROUND(AVG(cu2_grade)::numeric, 2) AS avg_semester2_grade
        FROM fact_enrollments
    """,
    "dropout_by_scholarship": """
        SELECT
            ds.scholarship_holder,
            fe.enrollment_status,
            COUNT(*) AS student_count
        FROM fact_enrollments fe
        JOIN dim_student ds ON fe.student_id = ds.student_id
        GROUP BY ds.scholarship_holder, fe.enrollment_status
        ORDER BY ds.scholarship_holder, fe.enrollment_status
    """,
    "dropout_by_age_group": """
        SELECT
            CASE
                WHEN ds.age_at_enrollment < 20 THEN 'Under 20'
                WHEN ds.age_at_enrollment BETWEEN 20 AND 24 THEN '20-24'
                WHEN ds.age_at_enrollment BETWEEN 25 AND 29 THEN '25-29'
                WHEN ds.age_at_enrollment BETWEEN 30 AND 39 THEN '30-39'
                ELSE '40+'
            END AS age_group,
            fe.enrollment_status,
            COUNT(*) AS student_count
        FROM fact_enrollments fe
        JOIN dim_student ds ON fe.student_id = ds.student_id
        GROUP BY age_group, fe.enrollment_status
        ORDER BY age_group, fe.enrollment_status
    """,
    "dropout_by_gender": """
        SELECT
            CASE WHEN ds.gender = 1 THEN 'Male' ELSE 'Female' END AS gender,
            fe.enrollment_status,
            COUNT(*) AS student_count
        FROM fact_enrollments fe
        JOIN dim_student ds ON fe.student_id = ds.student_id
        GROUP BY gender, fe.enrollment_status
        ORDER BY gender, fe.enrollment_status
    """,
    "dropout_by_debtor": """
        SELECT
            ds.debtor,
            ds.tuition_fees_up_to_date,
            fe.enrollment_status,
            COUNT(*) AS student_count
        FROM fact_enrollments fe
        JOIN dim_student ds ON fe.student_id = ds.student_id
        GROUP BY ds.debtor, ds.tuition_fees_up_to_date, fe.enrollment_status
        ORDER BY ds.debtor, fe.enrollment_status
    """,
    "feature_importance": pd.DataFrame({
        "feature": [
            "cu2_approved", "cu1_approved", "cu2_grade", "cu1_grade",
            "tuition_fees_up_to_date", "age_at_enrollment", "cu2_evaluations",
            "cu1_evaluations", "cu1_enrolled", "scholarship_holder"
        ],
        "importance": [
            0.2555, 0.1492, 0.1359, 0.0846,
            0.0707, 0.0498, 0.0420,
            0.0302, 0.0232, 0.0224
        ]
    })
}

print("Exporting tables to data/powerbi_exports/...\n")

with engine.connect() as conn:
    for name, query in queries.items():
        try:
            if isinstance(query, pd.DataFrame):
                df = query
            else:
                df = pd.read_sql(text(query), conn)
            path = f"data/powerbi_exports/{name}.csv"
            df.to_csv(path, index=False)
            print(f"{name}.csv — {len(df)} rows")
        except Exception as e:
            print(f"{name} failed: {e}")

print("\nAll CSVs saved to data/powerbi_exports/")
print("Upload these files to app.powerbi.com to build your dashboard.")