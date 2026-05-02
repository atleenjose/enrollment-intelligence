import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import pickle

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix

load_dotenv()

#Load data from the database
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

#feature engineering
drop_cols = ["enrollment_id", "student_id", "course_id", "economics_id"]
df = df.drop(columns=drop_cols)

df = df[df["enrollment_status"] != "Enrolled"]
print(f"After filtering Enrolled: {len(df)} rows")

le = LabelEncoder()
df["target"] = le.fit_transform(df["enrollment_status"])  # Dropout=0, Graduate=1
print(f"Classes: {le.classes_}")

X = df.drop(columns=["enrollment_status", "target"])
y = df["target"]

#test train split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train: {len(X_train)} | Test: {len(X_test)}")

#train model
print("\nTraining Random Forest...")
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    class_weight="balanced"
)
model.fit(X_train, y_train)

#evaluate model
y_pred = model.predict(X_test)

print("\n--- Classification Report ---")
print(classification_report(y_test, y_pred, target_names=le.classes_))

print("--- Confusion Matrix ---")
print(confusion_matrix(y_test, y_pred))

#importance of features
print("\n--- Top 10 Features ---")
feat_imp = pd.DataFrame({
    "feature": X.columns,
    "importance": model.feature_importances_
}).sort_values("importance", ascending=False)

print(feat_imp.head(10).to_string(index=False))

#save model and encoders
os.makedirs("models", exist_ok=True)

with open("models/dropout_model.pkl", "wb") as f:
    pickle.dump(model, f)

with open("models/label_encoder.pkl", "wb") as f:
    pickle.dump(le, f)

with open("models/feature_columns.pkl", "wb") as f:
    pickle.dump(list(X.columns), f)

print("\nModel saved to models/dropout_model.pkl ✅")