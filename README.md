# Student Enrollment Intelligence System

An end-to-end data engineering and machine learning project that predicts student dropout risk, surfaces explainable AI insights, and exposes results via a live REST API.

## Live Demo
**API:** https://enrollment-intelligence.onrender.com/docs

## Architecture
```
Raw Data (Kaggle)
      |
      v
ETL Pipeline (Python)
      |
      v
PostgreSQL Star Schema (Neon cloud)
      |
      v
ML Models (Random Forest + Logistic Regression)
      |
      v
SHAP Explainability Layer
      |
      v
FastAPI (deployed on Render)
      |
      v
Power BI Dashboard
```

## Stack
- **Database:** PostgreSQL · Star schema (fact_enrollments, dim_student, dim_course, dim_economics)
- **ETL:** Python · pandas · SQLAlchemy · validation layer · Faker synthetic data
- **ML:** scikit-learn · Random Forest (90% accuracy, ROC-AUC 0.9478) · Logistic Regression baseline (ROC-AUC 0.9473)
- **Explainability:** SHAP TreeExplainer · global feature importance · per-student risk factors
- **API:** FastAPI · 3 endpoints · deployed on Render
- **Dashboard:** Power BI web · 6 visuals across KPIs, enrollment outcomes, and ML insights
- **Cloud:** Neon (PostgreSQL) · Render (API)

## API Endpoints
| Endpoint | Method | Description |
| `/predict` | POST | Dropout risk prediction + SHAP reasons |
| `/student_summary/{id}` | GET | Student profile + enrollment status |
| `/kpi_metrics` | GET | Institution-wide enrollment KPIs |
| `/health` | GET | Health check |

## Key Findings
- Students who fail to pay tuition have significantly higher dropout rates
- Semester 1 and 2 approved units are the strongest dropout predictors (SHAP)
- Scholarship holders graduate at nearly 2x the rate of non-scholarship students
- Younger students (under 24) make up the majority of dropouts by volume

## Dataset
- 4,424 students · 35 features · sourced from Kaggle
- Synthetic tables generated: financial_aid (2,600+ rows) · applications (4,424 rows)

## Setup
```bash
git clone https://github.com/atleenjose/enrollment-intelligence
cd enrollment-intelligence
pip install -r requirements.txt
python models/train_model.py
uvicorn api.main:app --reload
```

## Project Structure
```
enrollment_intelligence/
├── api/
│   └── main.py                 # FastAPI app with 3 endpoints
├── models/
│   ├── train_model.py          # RF + LR training + SHAP
│   ├── dropout_model.pkl
│   └── shap_explainer.pkl
├── pipeline/
│   ├── etl.py                  # Data cleaning + loading
│   ├── validate_records.py     # Validation layer
│   └── generate_synthetic.py  # Faker synthetic tables
├── database/
│   ├── schema.sql
│   └── kpis.sql
├── dashboard/
│   └── Dashboard Screenshot.png
├── render.yaml
└── requirements.txt
```