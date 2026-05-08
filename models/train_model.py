import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import pickle
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
import shap

load_dotenv()

#Database connection
engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

query = """
SELECT 
    fe.*,
    ds.age_at_enrollment,
    ds.gender,
    ds.scholarship_holder,
    ds.debtor,
    ds.tuition_fees_up_to_date,
    ds.displaced,
    ds.educational_special_needs,
    ds.marital_status,
    ds.international,
    de.unemployment_rate,
    de.inflation_rate,
    de.gdp
FROM fact_enrollments fe
JOIN dim_student ds ON fe.student_id = ds.student_id
JOIN dim_economics de ON fe.economics_id = de.economics_id
"""

df = pd.read_sql(query, engine)
print(f"Loaded {len(df)} rows")

#Feature engineering
drop_cols = ["enrollment_id", "student_id", "course_id", "economics_id"]
df = df.drop(columns=drop_cols)

df = df[df["enrollment_status"] != "Enrolled"]
print(f"After filtering Enrolled: {len(df)} rows")

le = LabelEncoder()
df["target"] = le.fit_transform(df["enrollment_status"])  # Dropout=0, Graduate=1
print(f"Classes: {le.classes_}")

X = df.drop(columns=["enrollment_status", "target"])
y = df["target"]

#Train / test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train: {len(X_train)} | Test: {len(X_test)}")

#1. Random Forest
print("\n" + "="*50)
print("Training Random Forest...")
rf_model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    class_weight="balanced",
)
rf_model.fit(X_train, y_train)

rf_pred  = rf_model.predict(X_test)
rf_proba = rf_model.predict_proba(X_test)[:, 1]
rf_auc   = roc_auc_score(y_test, rf_proba)

print("\n Random Forest - Classification Report ")
print(classification_report(y_test, rf_pred, target_names=le.classes_))
print(" Confusion Matrix ")
print(confusion_matrix(y_test, rf_pred))
print(f"ROC-AUC: {rf_auc:.4f}")

#2. Logistic Regression (baseline) 
print("\n" + "="*50)
print("Training Logistic Regression (baseline)...")

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)

lr_model = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
lr_model.fit(X_train_scaled, y_train)

lr_pred  = lr_model.predict(X_test_scaled)
lr_proba = lr_model.predict_proba(X_test_scaled)[:, 1]
lr_auc   = roc_auc_score(y_test, lr_proba)

print("\n Logistic Regression - Classification Report ")
print(classification_report(y_test, lr_pred, target_names=le.classes_))
print(" Confusion Matrix ")
print(confusion_matrix(y_test, lr_pred))
print(f"ROC-AUC: {lr_auc:.4f}")

#Model comparison
print("\n" + "="*50)
print("MODEL COMPARISON")
print(f"  Random Forest  ROC-AUC : {rf_auc:.4f}")
print(f"  Logistic Reg.  ROC-AUC : {lr_auc:.4f}")
winner = "Random Forest" if rf_auc >= lr_auc else "Logistic Regression"
print(f"  Winner: {winner}")

#3. Feature importance (RF) 
print("\n Top 10 Features (Random Forest) ")
feat_imp = pd.DataFrame({
    "feature":    X.columns,
    "importance": rf_model.feature_importances_,
}).sort_values("importance", ascending=False)
print(feat_imp.head(10).to_string(index=False))

#4. SHAP explainability 
print("\n" + "="*50)
print("Generating SHAP explanations...")

explainer   = shap.TreeExplainer(rf_model)
shap_values = explainer.shap_values(X_test)

# shap_values shape depends on shap version:
# older - list [class0_array, class1_array]
# newer - single 3D array (n_samples, n_features, n_classes)
if isinstance(shap_values, list):
    sv_class1= shap_values[1]# dropout class SHAP values
    expected_val_class1 = explainer.expected_value[1]
else:
    sv_class1= shap_values[:, :, 1]
    expected_val_class1 = explainer.expected_value[1] if hasattr(explainer.expected_value, "__len__") else explainer.expected_value

# Global summary plot
shap.summary_plot(
    sv_class1,
    X_test,
    feature_names=X_test.columns.tolist(),
    show=False,
)
plt.tight_layout()
plt.savefig("models/shap_summary.png", bbox_inches="tight", dpi=150)
plt.close()
print("Saved: models/shap_summary.png")

# Per-student force plot (first student in test set)
shap.force_plot(
    expected_val_class1,
    sv_class1[0],
    X_test.iloc[0],
    matplotlib=True,
    show=False,
)
plt.tight_layout()
plt.savefig("models/shap_student_example.png", bbox_inches="tight", dpi=150)
plt.close()
print("Saved: models/shap_student_example.png")


def explain_student(student_df: pd.DataFrame) -> list[str]:
    """Return top-3 human-readable risk factors for one student row."""
    sv_raw = explainer.shap_values(student_df)
    sv = sv_raw[1][0] if isinstance(sv_raw, list) else sv_raw[0, :, 1]
    feature_names = student_df.columns.tolist()
    top3    = sorted(zip(feature_names, sv), key=lambda x: abs(x[1]), reverse=True)[:3]
    reasons = []
    for feat, val in top3:
        direction = "increases" if val > 0 else "decreases"
        reasons.append(f"{feat} {direction} dropout risk")
    return reasons


#5. Save all artifacts 
os.makedirs("models", exist_ok=True)

with open("models/dropout_model.pkl", "wb") as f:
    pickle.dump(rf_model, f)

with open("models/label_encoder.pkl", "wb") as f:
    pickle.dump(le, f)

with open("models/feature_columns.pkl", "wb") as f:
    pickle.dump(list(X.columns), f)

joblib.dump(scaler,    "models/scaler.pkl")
joblib.dump(explainer, "models/shap_explainer.pkl")

print("\n  All artifacts saved:")
print("    models/dropout_model.pkl")
print("    models/label_encoder.pkl")
print("    models/feature_columns.pkl")
print("    models/scaler.pkl")
print("    models/shap_explainer.pkl")
print("    models/shap_summary.png")
print("    models/shap_student_example.png")