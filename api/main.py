import os
import pickle
import joblib
import httpx
import re
from pathlib import Path
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

#DB engine
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
    try:
        artifacts["explainer"] = joblib.load(MODEL_DIR / "shap_explainer.pkl")
        print("SHAP explainer loaded")
    except Exception as e:
        print(f"SHAP explainer failed to load: {e}")
        artifacts["explainer"] = None
    artifacts["engine"] = get_engine()
    yield
    artifacts.clear()

app = FastAPI(
    title="Enrollment Intelligence API",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#Schemas──
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

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    student_id: int | None = None

#SHAP helper
def get_shap_reasons(input_df: pd.DataFrame) -> list[str]:
    explainer = artifacts.get("explainer")
    if explainer is None:
        return ["SHAP explainer not available"]
    try:
        shap_vals = explainer.shap_values(input_df)
        sv = shap_vals[1][0] if isinstance(shap_vals, list) else shap_vals[0, :, 1]
        feature_names = input_df.columns.tolist()
        top3 = sorted(zip(feature_names, sv), key=lambda x: abs(x[1]), reverse=True)[:3]
        return [f"{feat} {'increases' if val > 0 else 'decreases'} dropout risk" for feat, val in top3]
    except Exception as e:
        return [f"Explanation error: {str(e)}"]

#Student data fetcher 
def fetch_student_data(student_id: int, engine):
    query = text("""
        SELECT
            ds.student_id,
            ds.age_at_enrollment,
            ds.gender,
            ds.scholarship_holder,
            ds.debtor,
            ds.tuition_fees_up_to_date,
            ds.displaced,
            ds.educational_special_needs,
            ds.marital_status,
            ds.international,
            fe.enrollment_status,
            fe.cu1_credited,
            fe.cu1_enrolled,
            fe.cu1_evaluations,
            fe.cu1_approved,
            fe.cu1_grade,
            fe.cu1_without_eval,
            fe.cu2_credited,
            fe.cu2_enrolled,
            fe.cu2_evaluations,
            fe.cu2_approved,
            fe.cu2_grade,
            fe.cu2_without_eval,
            de.unemployment_rate,
            de.inflation_rate,
            de.gdp
        FROM dim_student ds
        JOIN fact_enrollments fe ON ds.student_id = fe.student_id
        JOIN dim_economics de    ON fe.economics_id = de.economics_id
        WHERE ds.student_id = :sid
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(query, {"sid": student_id}).fetchone()

def build_input_df(row, features):
    input_data = {
        "cu1_credited": row[11], "cu1_enrolled": row[12],
        "cu1_evaluations": row[13], "cu1_approved": row[14],
        "cu1_grade": float(row[15]), "cu1_without_eval": row[16],
        "cu2_credited": row[17], "cu2_enrolled": row[18],
        "cu2_evaluations": row[19], "cu2_approved": row[20],
        "cu2_grade": float(row[21]), "cu2_without_eval": row[22],
        "age_at_enrollment": row[1], "gender": row[2],
        "scholarship_holder": row[3], "debtor": row[4],
        "tuition_fees_up_to_date": row[5], "displaced": row[6],
        "educational_special_needs": row[7], "marital_status": row[8],
        "international": row[9], "unemployment_rate": float(row[23]),
        "inflation_rate": float(row[24]), "gdp": float(row[25]),
    }
    return pd.DataFrame([{f: input_data[f] for f in features}])

#Routes
@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0.0"}


@app.post("/predict", response_model=PredictionResponse)
def predict(student: StudentFeatures):
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

    return PredictionResponse(
        prediction=encoder.inverse_transform([prediction_idx])[0],
        dropout_probability=dropout_prob,
        graduate_probability=graduate_prob,
        risk_level=risk_level,
        top_risk_factors=get_shap_reasons(input_df),
    )


@app.get("/student_summary/{student_id}")
def student_summary(student_id: int):
    engine   = artifacts.get("engine")
    features = artifacts.get("features")
    model    = artifacts.get("model")
    encoder  = artifacts.get("encoder")

    if not engine:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        row = fetch_student_data(student_id, engine)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")

    if not row:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

    ml_prediction = None
    if all([features, model, encoder]):
        try:
            input_df  = build_input_df(row, features)
            proba     = model.predict_proba(input_df.values)[0]
            pred_idx  = model.predict(input_df.values)[0]
            dropout_p = round(float(proba[0]) * 100, 2)
            ml_prediction = {
                "prediction":          encoder.inverse_transform([pred_idx])[0],
                "dropout_probability": dropout_p,
                "risk_level":          "High" if dropout_p >= 60 else "Medium" if dropout_p >= 35 else "Low",
                "top_risk_factors":    get_shap_reasons(input_df),
            }
        except Exception:
            pass

    return {
        "student_id":         row[0],
        "age_at_enrollment":  row[1],
        "gender":             "Male" if row[2] == 1 else "Female",
        "scholarship_holder": bool(row[3]),
        "debtor":             bool(row[4]),
        "tuition_up_to_date": bool(row[5]),
        "enrollment_status":  row[10],
        "semester1_grade":    float(row[15]),
        "semester2_grade":    float(row[21]),
        "semester1_approved": row[14],
        "semester2_approved": row[20],
        "ml_prediction":      ml_prediction,
    }


@app.get("/kpi_metrics")
def kpi_metrics():
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
        "total_students":      row[0],
        "graduated":           row[1],
        "dropped_out":         row[2],
        "currently_enrolled":  row[3],
        "graduation_rate_pct": row[4],
        "dropout_rate_pct":    row[5],
        "avg_semester1_grade": row[6],
        "avg_semester2_grade": row[7],
    }


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    Ask anything in plain English.
    Examples: 'Why is student 5 at risk?' or 'What is the overall dropout rate?'
    Powered by Claude AI with real student data and SHAP explanations.
    """
    anthropic_key = os.getenv("GROQ_API_KEY")
    if not anthropic_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    question   = request.question.strip()
    engine     = artifacts.get("engine")
    match      = re.search(r'\b(\d+)\b', question)
    student_id = int(match.group(1)) if match else None
    context    = ""

    if student_id and engine:
        try:
            row = fetch_student_data(student_id, engine)
            if row:
                features = artifacts.get("features")
                model    = artifacts.get("model")
                encoder  = artifacts.get("encoder")
                shap_facts = []
                dropout_p  = None
                prediction = None

                if all([features, model, encoder]):
                    input_df   = build_input_df(row, features)
                    proba      = model.predict_proba(input_df.values)[0]
                    pred_idx   = model.predict(input_df.values)[0]
                    dropout_p  = round(float(proba[0]) * 100, 2)
                    prediction = encoder.inverse_transform([pred_idx])[0]
                    shap_facts = get_shap_reasons(input_df)

                context = f"""
Student {student_id}:
- Age: {row[1]}, Gender: {"Male" if row[2] == 1 else "Female"}
- Scholarship: {bool(row[3])}, Debtor: {bool(row[4])}, Tuition paid: {bool(row[5])}
- Current status: {row[10]}
- Semester 1: grade {float(row[15]):.2f}, approved {row[14]} of {row[12]} units
- Semester 2: grade {float(row[21]):.2f}, approved {row[20]} of {row[18]} units
- ML prediction: {prediction}, Dropout probability: {dropout_p}%
- Top SHAP risk factors: {', '.join(shap_facts)}
"""
            else:
                context = f"Student {student_id} not found in the database."
        except Exception as e:
            context = f"Could not fetch student data: {str(e)}"

    elif engine:
        try:
            kpi_query = text("""
                SELECT COUNT(*),
                    ROUND((100.0 * SUM(CASE WHEN enrollment_status='Dropout' THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0))::numeric,2),
                    ROUND((100.0 * SUM(CASE WHEN enrollment_status='Graduate' THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0))::numeric,2)
                FROM fact_enrollments
            """)
            with engine.connect() as conn:
                row = conn.execute(kpi_query).fetchone()
            context = f"{row[0]} total students, {row[2]}% graduation rate, {row[1]}% dropout rate."
        except Exception:
            context = "Institution enrollment data available."

    system_prompt = """You are an academic advisor assistant for a university enrollment intelligence system.
You have real student data and ML predictions from a Random Forest model with SHAP explainability.
Answer in 3-4 sentences. Be clear, empathetic, and actionable. Explain things simply without jargon.
Never make up data not given to you."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "max_tokens": 300,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": f"Question: {question}\n\nData:\n{context}"},
                    ],
                },
            )
        resp_json = response.json()
        answer = resp_json["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")

    return AskResponse(answer=answer, student_id=student_id)