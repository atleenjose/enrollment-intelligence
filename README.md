# Enrollment Intelligence

End-to-end data engineering and ML project predicting student dropout risk.

## Architecture
Raw CSV - ETL Pipeline - PostgreSQL Star Schema - ML Model - FastAPI - Power BI Dashboard

## Tech Stack
- Python, Pandas, SQLAlchemy
- PostgreSQL
- scikit-learn (Random Forest, 90% accuracy)
- FastAPI
- Power BI

## Key Insights
- 32% dropout rate across 4,424 students
- Students aged 26-35 have highest dropout risk (57%)
- Scholarship holders are 3x less likely to drop out
- Semester 1 grades are the strongest dropout predictor

## PowerBI Dashboard
![Dashboard](dashboard/Dashboard%20Screenshot.png)

## API
> Deployment in progress — run locally with:
```bash
uvicorn api.main:app --reload
```
Then visit: http://127.0.0.1:8000/docs

## Quick Start
```bash
git clone https://github.com/atleenjose/enrollment-intelligence.git
cd enrollment-intelligence
pip install -r requirements.txt
uvicorn api.main:app --reload
```

## Project Structure
enrollment_intelligence/
├── api/
│   └── main.py              # FastAPI app
├── data/
│   ├── raw/                 # Original dataset
│   └── cleaned/             # Exported KPI CSVs
├── database/
│   ├── schema.sql           # Star schema definition
│   └── kpis.sql             # KPI queries
├── models/
│   ├── train_model.py       # ML training script
│   ├── dropout_model.pkl    # Trained model
│   └── feature_columns.pkl  # Feature definitions
├── pipeline/
│   └── etl.py               # ETL pipeline
├── dashboard/
│   └── Dashboard Screenshot.png
├── requirements.txt
└── README.md