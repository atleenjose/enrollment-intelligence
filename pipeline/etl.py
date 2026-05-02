import pandas as pd
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

def extract():
    print("Extracting data...")
    df = pd.read_csv("data/raw/students.csv")
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    return df

def transform(df):
    print("Transforming data...")
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("/", "_")
    df= df.rename(columns={"targert": "enrollment_status"})
    df= df.drop_duplicates()
    df= df.dropna()
    print(f"After cleaning: {len(df)} rows")
    return df

def load(df):
    print("Loading data...")
    df.to_sql("students", engine, if_exists="replace", index=False)
    print("Data loaded successfully.")

if __name__ == "__main__":
    df = extract()
    df = transform(df)
    load(df)