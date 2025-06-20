import streamlit as st
import pandas as pd
import numpy as np

# Constants
Z = 1.65
ks = 0.5
kr = 0.5
kp = 0.5
product_type_scaler = {"Fresh": 1.1, "Frozen": 1.05, "Dry": 1.0}
pareto_weight = {"X": 1.0, "A": 1.0, "B": 0.75, "C": 0.5}

# URLs
SHEET_ID = "117aUCWmv8zPtypTrIk-bGdYe_FppnGXcnm5rlsIlYVU"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"
DATA_URL = f"{BASE_URL}&sheet=data base"
RESCHED_URL = f"{BASE_URL}&sheet=reschedule"

@st.cache_data(ttl=86400)
def load_data():
    data_base = pd.read_csv(DATA_URL)
    resched = pd.read_csv(RESCHED_URL)
    return data_base, resched

# Load
st.title("📦 Dynamic DOI Calculator (Auto from GSheet)")
data_df, resched_df = load_data()
st.success("Loaded data from Google Sheets.")

# Standardize column names
data_df.columns = data_df.columns.str.strip().str.lower()
resched_df.columns = resched_df.columns.str.strip().str.lower()

# User Controls
st.sidebar.header("Apply Refined Logic To:")
selected_pareto = st.sidebar.multiselect("Pareto Classes", ["X", "A", "B", "C"], default=["X", "A"])
selected_demand = st.sidebar.multiselect("Demand Types", ["Stable", "Volatile", "Seasonal"], default=["Stable", "Volatile"])
include_safety = st.sidebar.checkbox("Include Safety (Demand Variability)", True)
include_reschedule = st.sidebar.checkbox("Include Reschedule Adjustment", True)
include_pareto = st.sidebar.checkbox("Include Pareto Buffer", True)

# Merge reschedule data
resched_df.rename(columns={"wh_id": "location_id"}, inplace=True)
merged = data_df.merge(resched_df, on=["location_id", "product_id"], how="left")
merged["resched_count"] = merged["resched_count"].fillna(0)
merged["total_inbound"] = merged["total_inbound"].fillna(1)

# DOI Logic
def compute_doi(row):
    base_doi = row["doi_policy"]
    apply_logic = row["pareto"] in selected_pareto and row["demand_type"] in selected_demand
    
    if not apply_logic:
        return round(base_doi, 2)

    safety = (
        Z * np.sqrt((row["std_leadtime"] ** 2) + (row["leadtime"] ** 2) * (row["std_demand"] / row["avg_demand"]) ** 2) * ks
        if include_safety else 0
    )
    resched = (
        kr * row["leadtime"] * (row["resched_count"] / row["total_inbound"])
        if include_reschedule else 0
    )
    pareto_val = kp * pareto_weight.get(row["pareto"], 0) if include_pareto else 0
    multiplier = product_type_scaler.get(row["product_type"], 1.0)

    return round(0.7 * (base_doi + safety + resched + pareto_val) * multiplier, 2)

# Compute final DOI
merged["final_doi"] = merged.apply(compute_doi, axis=1)

# Output
st.subheader("📊 Result Preview")
st.dataframe(merged[["location_id", "product_id", "doi_policy", "final_doi"]])

st.download_button("📥 Download Refined DOI", merged.to_csv(index=False), "refined_doi_output.csv")
