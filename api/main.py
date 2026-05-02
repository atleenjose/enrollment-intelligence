import pickle
from pathlib import Path
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MODEL_DIR = Path("models")

def load_artifact(filename):
    path = MODEL_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")
    with open(path, "rb") as f:
        return pickle.load(f)

artifacts = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    artifacts["model"] = load_artifact("dropout_model.pkl")
    artifacts["encoder"] = load_artifact("label_encoder.pkl")
    artifacts["features"] = load_artifact("feature_columns.pkl")
    yield
    artifacts.clear()

app = FastAPI(
    title="Enrollment Intelligence API",
    version="1.0.0",
    lifespan=lifespan
)

class StudentFeatures(BaseModel):
    cu1_credited: int = Field(0, ge=0)
    cu1_enrolled: int = Field(6, ge=0)
    cu1_evaluations: int = Field(6, ge=0)
    cu1_approved: int = Field(5, ge=0)
    cu1_grade: float = Field(12.0, ge=0, le=20)
    cu1_without_eval: int = Field(0, ge=0)
    cu2_credited: int = Field(0, ge=0)
    cu2_enrolled: int = Field(6, ge=0)
    cu2_evaluations: int = Field(6, ge=0)
    cu2_approved: int = Field(5, ge=0)
    cu2_grade: float = Field(12.0, ge=0, le=20)
    cu2_without_eval: int = Field(0, ge=0)
    age_at_enrollment: int = Field(20, ge=15, le=70)
    gender: int = Field(1, ge=0, le=1)
    scholarship_holder: int = Field(0, ge=0, le=1)
    debtor: int = Field(0, ge=0, le=1)
    tuition_fees_up_to_date: int = Field(1, ge=0, le=1)
    displaced: int = Field(0, ge=0, le=1)
    educational_special_needs: int = Field(0, ge=0, le=1)
    marital_status: int = Field(1, ge=0)
    international: int = Field(0, ge=0, le=1)
    unemployment_rate: float = Field(10.8)
    inflation_rate: float = Field(1.4)
    gdp: float = Field(1.74)

class PredictionResponse(BaseModel):
    prediction: str
    dropout_probability: float
    graduate_probability: float
    risk_level: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict", response_model=PredictionResponse)
def predict(student: StudentFeatures):
    model = artifacts.get("model")
    encoder = artifacts.get("encoder")
    features = artifacts.get("features")

    if not all([model, encoder, features]):
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        input_vector = np.array([[getattr(student, f) for f in features]])
        prediction_idx = model.predict(input_vector)[0]
        probabilities = model.predict_proba(input_vector)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

    dropout_prob = round(float(probabilities[0]) * 100, 2)
    graduate_prob = round(float(probabilities[1]) * 100, 2)

    risk_level = (
        "High" if dropout_prob >= 60
        else "Medium" if dropout_prob >= 35
        else "Low"
    )

    return PredictionResponse(
        prediction=encoder.inverse_transform([prediction_idx])[0],
        dropout_probability=dropout_prob,
        graduate_probability=graduate_prob,
        risk_level=risk_level,
    )