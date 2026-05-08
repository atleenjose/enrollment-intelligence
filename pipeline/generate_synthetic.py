import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from faker import Faker
import os
import random
from datetime import datetime

load_dotenv()
fake = Faker()
random.seed(42)
Faker.seed(42)

#DB connection
engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

print("="*55)
print("  ENROLLMENT INTELLIGENCE — SYNTHETIC DATA GENERATOR")
print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*55)

#Fetch existing student IDs
with engine.connect() as conn:
    result = conn.execute(text("SELECT student_id FROM dim_student ORDER BY student_id"))
    student_ids = [row[0] for row in result.fetchall()]

print(f"\nFound {len(student_ids)} students in dim_student")

#Create tables
with engine.connect() as conn:

    conn.execute(text("""
        DROP TABLE IF EXISTS financial_aid CASCADE;
        CREATE TABLE financial_aid (
            aid_id        SERIAL PRIMARY KEY,
            student_id    INT REFERENCES dim_student(student_id),
            aid_type      VARCHAR(50),
            amount_usd    NUMERIC(10, 2),
            awarded_date  DATE,
            academic_year VARCHAR(10)
        )
    """))

    conn.execute(text("""
        DROP TABLE IF EXISTS applications CASCADE;
        CREATE TABLE applications (
            app_id           SERIAL PRIMARY KEY,
            student_id       INT REFERENCES dim_student(student_id),
            application_date DATE,
            program          VARCHAR(100),
            application_mode VARCHAR(50),
            status           VARCHAR(30),
            decision_date    DATE,
            interview_score  NUMERIC(4, 2)
        )
    """))

    conn.commit()
    print("Tables created: financial_aid, applications")

#Generate financial_aid data
print("\nGenerating financial_aid records...")

aid_types    = ["Merit", "Need-based", "Athletic", "Government Grant", "Institutional Grant"]
academic_yrs = ["2019/20", "2020/21", "2021/22", "2022/23"]

aid_records = []
for sid in student_ids:
    # ~60% of students receive some form of aid
    if random.random() < 0.60:
        num_awards = random.choices([1, 2], weights=[0.80, 0.20])[0]
        for _ in range(num_awards):
            awarded = fake.date_between(start_date="-5y", end_date="-1y")
            aid_records.append({
                "student_id":    sid,
                "aid_type":      random.choice(aid_types),
                "amount_usd":    round(random.uniform(500, 9000), 2),
                "awarded_date":  awarded,
                "academic_year": random.choice(academic_yrs),
            })

aid_df = pd.DataFrame(aid_records)
aid_df.to_sql("financial_aid", engine, if_exists="append", index=False)
print(f" Inserted {len(aid_df)} financial_aid records")

#Generate applications data
print("\nGenerating applications records...")

programs = [
    "Computer Science", "Business Administration", "Nursing",
    "Civil Engineering", "Electrical Engineering", "Management",
    "Communication Design", "Social Service", "Tourism", "Biofuel Production",
]
app_modes  = ["Online", "In-person", "Agent", "Transfer", "International"]
app_status = ["Admitted", "Waitlisted", "Rejected"]
# Weight towards Admitted since these are enrolled students
status_weights = [0.70, 0.15, 0.15]

app_records = []
for sid in student_ids:
    app_date     = fake.date_between(start_date="-6y", end_date="-3y")
    decision_date = fake.date_between(start_date=app_date, end_date="-2y")
    status       = random.choices(app_status, weights=status_weights)[0]
    app_records.append({
        "student_id":        sid,
        "application_date":  app_date,
        "program":           random.choice(programs),
        "application_mode":  random.choice(app_modes),
        "status":            status,
        "decision_date":     decision_date,
        "interview_score":   round(random.uniform(50, 100), 2) if status == "Admitted" else None,
    })

app_df = pd.DataFrame(app_records)
app_df.to_sql("applications", engine, if_exists="append", index=False)
print(f" Inserted {len(app_df)} applications records")

#Summary stats
print("\n" + "="*55)
print("SYNTHETIC DATA SUMMARY")
print("-"*40)
print(f"  financial_aid rows : {len(aid_df)}")
print(f"  Aid types breakdown:")
print(aid_df["aid_type"].value_counts().to_string())
print(f"\n  applications rows  : {len(app_df)}")
print(f"  Status breakdown:")
print(app_df["status"].value_counts().to_string())
print("="*55)