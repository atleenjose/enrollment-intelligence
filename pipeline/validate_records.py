import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

#DB connection
engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

print("="*55)
print("  ENROLLMENT INTELLIGENCE — VALIDATION LAYER")
print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*55)

results = []

with engine.connect() as conn:

    #Check 1: Students in fact but missing from dim_student
    mismatched = pd.read_sql(text("""
        SELECT f.student_id
        FROM fact_enrollments f
        LEFT JOIN dim_student s ON f.student_id = s.student_id
        WHERE s.student_id IS NULL
    """), conn)
    results.append(("mismatched_student_ids", len(mismatched)))
    print(f"\n[1] Mismatched student IDs (fact but not in dim_student): {len(mismatched)}")
    if len(mismatched) > 0:
        print(mismatched.head(5).to_string(index=False))

    #Check 2: Duplicate enrollment records
    duplicates = pd.read_sql(text("""
        SELECT student_id, COUNT(*) AS cnt
        FROM fact_enrollments
        GROUP BY student_id
        HAVING COUNT(*) > 1
    """), conn)
    results.append(("duplicate_enrollments", len(duplicates)))
    print(f"\n[2] Students with duplicate enrollment records: {len(duplicates)}")
    if len(duplicates) > 0:
        print(duplicates.head(5).to_string(index=False))

    #Check 3: Null enrollment status
    null_status = pd.read_sql(text("""
        SELECT student_id, enrollment_status
        FROM fact_enrollments
        WHERE enrollment_status IS NULL
    """), conn)
    results.append(("null_enrollment_status", len(null_status)))
    print(f"\n[3] Records with NULL enrollment status: {len(null_status)}")

    #Check 4: Invalid grade values (outside 0–20 range)
    invalid_grades = pd.read_sql(text("""
        SELECT student_id, cu1_grade, cu2_grade
        FROM fact_enrollments
        WHERE cu1_grade < 0 OR cu1_grade > 20
           OR cu2_grade < 0 OR cu2_grade > 20
    """), conn)
    results.append(("invalid_grade_values", len(invalid_grades)))
    print(f"\n[4] Records with invalid grade values (outside 0–20): {len(invalid_grades)}")
    if len(invalid_grades) > 0:
        print(invalid_grades.head(5).to_string(index=False))

    #Check 5: Students with approved > enrolled (impossible)
    approved_gt_enrolled = pd.read_sql(text("""
        SELECT student_id, cu1_enrolled, cu1_approved, cu2_enrolled, cu2_approved
        FROM fact_enrollments
        WHERE cu1_approved > cu1_enrolled
           OR cu2_approved > cu2_enrolled
    """), conn)
    results.append(("approved_exceeds_enrolled", len(approved_gt_enrolled)))
    print(f"\n[5] Records where approved units > enrolled units: {len(approved_gt_enrolled)}")
    if len(approved_gt_enrolled) > 0:
        print(approved_gt_enrolled.head(5).to_string(index=False))

    #Check 6: Missing economics reference
    missing_econ = pd.read_sql(text("""
        SELECT f.student_id, f.economics_id
        FROM fact_enrollments f
        LEFT JOIN dim_economics e ON f.economics_id = e.economics_id
        WHERE e.economics_id IS NULL
    """), conn)
    results.append(("missing_economics_ref", len(missing_econ)))
    print(f"\n[6] Records with missing economics reference: {len(missing_econ)}")

    #Write validation report to DB
    print("\n" + "="*55)
    print("Saving validation report to database...")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS validation_report (
            id          SERIAL PRIMARY KEY,
            check_name  TEXT NOT NULL,
            issue_count INT  NOT NULL,
            status      TEXT NOT NULL,
            run_at      TIMESTAMP DEFAULT NOW()
        )
    """))

    for check_name, count in results:
        status = "PASS" if count == 0 else "FAIL"
        conn.execute(text("""
            INSERT INTO validation_report (check_name, issue_count, status, run_at)
            VALUES (:check, :count, :status, NOW())
        """), {"check": check_name, "count": count, "status": status})

    conn.commit()

#Summary
print("\nVALIDATION SUMMARY")
print("-"*40)
total_issues = 0
for check_name, count in results:
    status = "PASS" if count == 0 else "FAIL"
    print(f"  {status}  {check_name}: {count} issues")
    total_issues += count

print("-"*40)
print(f"  Total issues found: {total_issues}")
print("  Validation report saved to: validation_report table")
print("="*55)