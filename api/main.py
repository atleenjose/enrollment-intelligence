import os
import pickle
import joblib
from pathlib import Path
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

MODEL_DIR = Path("models")

#Artifact loader
def load_artifact(filename):
    path = MODEL_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")
    with open(path, "rb") as f:
        return pickle.load(f)

artifacts = {}

#DB engine (shared)
def get_engine():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return create_engine(db_url)
    return create_engine(
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )

#Startup / shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    artifacts["model"]    = load_artifact("dropout_model.pkl")
    artifacts["encoder"]  = load_artifact("label_encoder.pkl")
    artifacts["features"] = load_artifact("feature_columns.pkl")
    artifacts["scaler"]   = joblib.load(MODEL_DIR / "scaler.pkl")
    artifacts["explainer"] = joblib.load(MODEL_DIR / "shap_explainer.pkl")
    artifacts["engine"]   = get_engine()
    yield
    artifacts.clear()

app = FastAPI(
    title="Enrollment Intelligence API",
    version="2.0.0",
    lifespan=lifespan,
)

#Schemas
class StudentFeatures(BaseModel):
    cu1_credited: int              = Field(0,    ge=0)
    cu1_enrolled: int              = Field(6,    ge=0)
    cu1_evaluations: int           = Field(6,    ge=0)
    cu1_approved: int              = Field(5,    ge=0)
    cu1_grade: float               = Field(12.0, ge=0, le=20)
    cu1_without_eval: int          = Field(0,    ge=0)
    cu2_credited: int              = Field(0,    ge=0)
    cu2_enrolled: int              = Field(6,    ge=0)
    cu2_evaluations: int           = Field(6,    ge=0)
    cu2_approved: int              = Field(5,    ge=0)
    cu2_grade: float               = Field(12.0, ge=0, le=20)
    cu2_without_eval: int          = Field(0,    ge=0)
    age_at_enrollment: int         = Field(20,   ge=15, le=70)
    gender: int                    = Field(1,    ge=0, le=1)
    scholarship_holder: int        = Field(0,    ge=0, le=1)
    debtor: int                    = Field(0,    ge=0, le=1)
    tuition_fees_up_to_date: int   = Field(1,    ge=0, le=1)
    displaced: int                 = Field(0,    ge=0, le=1)
    educational_special_needs: int = Field(0,    ge=0, le=1)
    marital_status: int            = Field(1,    ge=0)
    international: int             = Field(0,    ge=0, le=1)
    unemployment_rate: float       = Field(10.8)
    inflation_rate: float          = Field(1.4)
    gdp: float                     = Field(1.74)

class PredictionResponse(BaseModel):
    prediction: str
    dropout_probability: float
    graduate_probability: float
    risk_level: str
    top_risk_factors: list[str]

#Helper: SHAP explanation 
def get_shap_reasons(input_df: pd.DataFrame) -> list[str]:
    explainer = artifacts["explainer"]
    shap_vals = explainer.shap_values(input_df)
    # Handle both old shap (list) and new shap (3D array)
    sv = shap_vals[1][0] if isinstance(shap_vals, list) else shap_vals[0, :, 1]
    feature_names = input_df.columns.tolist()
    top3 = sorted(zip(feature_names, sv), key=lambda x: abs(x[1]), reverse=True)[:3]
    reasons = []
    for feat, val in top3:
        direction = "increases" if val > 0 else "decreases"
        reasons.append(f"{feat} {direction} dropout risk")
    return reasons

#Routes
@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/predict", response_model=PredictionResponse)
def predict(student: StudentFeatures):
    """
    Predict dropout risk for a single student.
    Returns prediction, probabilities, risk level, and top 3 SHAP risk factors.
    """
    model    = artifacts.get("model")
    encoder  = artifacts.get("encoder")
    features = artifacts.get("features")

    if not all([model, encoder, features]):
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        input_data   = {f: getattr(student, f) for f in features}
        input_df     = pd.DataFrame([input_data])
        input_vector = input_df.values

        prediction_idx = model.predict(input_vector)[0]
        probabilities  = model.predict_proba(input_vector)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

    dropout_prob  = round(float(probabilities[0]) * 100, 2)
    graduate_prob = round(float(probabilities[1]) * 100, 2)

    risk_level = (
        "High"   if dropout_prob >= 60 else
        "Medium" if dropout_prob >= 35 else
        "Low"
    )

    risk_factors = get_shap_reasons(input_df)

    return PredictionResponse(
        prediction=encoder.inverse_transform([prediction_idx])[0],
        dropout_probability=dropout_prob,
        graduate_probability=graduate_prob,
        risk_level=risk_level,
        top_risk_factors=risk_factors,
    )


@app.get("/student_summary/{student_id}")
def student_summary(student_id: int):
    """
    Return profile + enrollment status + dropout risk score for one student.
    """
    engine = artifacts.get("engine")
    if not engine:
        raise HTTPException(status_code=503, detail="Database not connected")

    query = text("""
        SELECT
            ds.student_id,
            ds.age_at_enrollment,
            ds.gender,
            ds.scholarship_holder,
            ds.debtor,
            ds.tuition_fees_up_to_date,
            fe.enrollment_status,
            fe.cu1_grade,
            fe.cu2_grade,
            fe.cu1_approved,
            fe.cu2_approved
        FROM dim_student ds
        JOIN fact_enrollments fe ON ds.student_id = fe.student_id
        WHERE ds.student_id = :sid
        LIMIT 1
    """)

    try:
        with engine.connect() as conn:
            row = conn.execute(query, {"sid": student_id}).fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")

    if not row:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

    return {
        "student_id":            row[0],
        "age_at_enrollment":     row[1],
        "gender":                "Male" if row[2] == 1 else "Female",
        "scholarship_holder":    bool(row[3]),
        "debtor":                bool(row[4]),
        "tuition_up_to_date":    bool(row[5]),
        "enrollment_status":     row[6],
        "semester1_grade":       row[7],
        "semester2_grade":       row[8],
        "semester1_approved":    row[9],
        "semester2_approved":    row[10],
    }


@app.get("/kpi_metrics")
def kpi_metrics():
    """
    Return institution-wide enrollment KPIs.
    """
    engine = artifacts.get("engine")
    if not engine:
        raise HTTPException(status_code=503, detail="Database not connected")

    query = text("""
        SELECT
            COUNT(*) AS total_students,
            SUM(CASE WHEN enrollment_status = 'Graduate' THEN 1 ELSE 0 END) AS graduated,
            SUM(CASE WHEN enrollment_status = 'Dropout'  THEN 1 ELSE 0 END) AS dropped_out,
            SUM(CASE WHEN enrollment_status = 'Enrolled' THEN 1 ELSE 0 END) AS currently_enrolled,
            ROUND((100.0 * SUM(CASE WHEN enrollment_status = 'Graduate' THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0))::numeric, 2) AS graduation_rate_pct,
            ROUND((100.0 * SUM(CASE WHEN enrollment_status = 'Dropout'  THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0))::numeric, 2) AS dropout_rate_pct,
            ROUND(AVG(cu1_grade)::numeric, 2) AS avg_semester1_grade,
            ROUND(AVG(cu2_grade)::numeric, 2) AS avg_semester2_grade
        FROM fact_enrollments
    """)

    try:
        with engine.connect() as conn:
            row = conn.execute(query).fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")

    return {
        "total_students":       row[0],
        "graduated":            row[1],
        "dropped_out":          row[2],
        "currently_enrolled":   row[3],
        "graduation_rate_pct":  row[4],
        "dropout_rate_pct":     row[5],
        "avg_semester1_grade":  row[6],
        "avg_semester2_grade":  row[7],
    }