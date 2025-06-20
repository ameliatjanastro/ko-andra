import streamlit as st
import pandas as pd
import numpy as np

# ---- Google Sheet Setup ----
SHEET_ID = "117aUCWmv8zPtypTrIk-bGdYe_FppnGXcnm5rlsIlYVU"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"
DATA_URL = f"{BASE_URL}&sheet=database"
RESCHED_URL = f"{BASE_URL}&sheet=reschedule"

@st.cache_data(ttl=86400)
def load_data():
    data_base = pd.read_csv(DATA_URL)
    resched = pd.read_csv(RESCHED_URL)
    return data_base, resched

# ---- App Title ----
st.set_page_config(page_title="Dynamic DOI Calculator", layout="wide")
st.title("📦 Dynamic DOI Calculator (GSheet Integrated)")

# ---- Load Data ----
with st.spinner("Loading data from Google Sheets..."):
    data_df, resched_df = load_data()
    st.success("Data successfully loaded!")

# ---- Standardize Columns ----
data_df.columns = data_df.columns.str.strip().str.lower()
resched_df.columns = resched_df.columns.str.strip().str.lower()

# ---- Sidebar: Module Toggle ----
st.sidebar.header("Select DOI Components to Include")
include_safety = st.sidebar.checkbox("✔️ Include Safety (Demand Variability)", True)
include_reschedule = st.sidebar.checkbox("✔️ Include Reschedule Adjustment", True)
include_pareto = st.sidebar.checkbox("✔️ Include Pareto Buffer", True)
include_multiplier = st.sidebar.checkbox("✔️ Include Product Type Multiplier", True)

# ---- Sidebar: Filter Scope ----
st.sidebar.header("Apply Logic To")
selected_pareto = st.sidebar.multiselect("Pareto Classes", ["X", "A", "B", "C", "D"], default=["X", "A"])
selected_demand = st.sidebar.multiselect("Demand Types", ["Stable", "Volatile", "Moderate"], default=["Volatile"])
selected_product_types = st.sidebar.multiselect("Product Types", ["Fresh", "Frozen", "Dry"], default=["Fresh", "Frozen", "Dry"])

# ---- Sidebar: Parameters ----
st.sidebar.header("📐 Model Parameters")
Z = st.sidebar.number_input("Z-Score (for service level)", value=1.65, step=0.05)

if include_safety:
    ks = st.sidebar.number_input("ks - Safety Scaling Factor", value=0.5, step=0.1)
else:
    ks = 0

if include_reschedule:
    kr = st.sidebar.number_input("kr - Reschedule Scaling Factor", value=0.5, step=0.1)
else:
    kr = 0

if include_pareto:
    kp = st.sidebar.number_input("kp - Pareto Scaling Factor", value=0.5, step=0.1)
    st.sidebar.markdown("#### Pareto Weights")
    weight_x = st.sidebar.number_input("Weight for Pareto X", value=1.0)
    weight_a = st.sidebar.number_input("Weight for Pareto A", value=1.0)
    weight_b = st.sidebar.number_input("Weight for Pareto B", value=0.75)
    weight_c = st.sidebar.number_input("Weight for Pareto C (and others)", value=0.5)
    pareto_weight = {"X": weight_x, "A": weight_a, "B": weight_b, "C": weight_c}
else:
    kp = 0
    pareto_weight = {"X": 0, "A": 0, "B": 0, "C": 0}

if include_multiplier:
    st.sidebar.markdown("#### Product Type Multipliers")
    fresh_mult = st.sidebar.number_input("Fresh Multiplier", value=1.1)
    frozen_mult = st.sidebar.number_input("Frozen Multiplier", value=1.05)
    dry_mult = st.sidebar.number_input("Dry Multiplier", value=1.0)
    product_type_scaler = {"Fresh": fresh_mult, "Frozen": frozen_mult, "Dry": dry_mult}
else:
    product_type_scaler = {"Fresh": 1.0, "Frozen": 1.0, "Dry": 1.0}

# ---- Merge Reschedule Data ----
resched_df = resched_df.rename(columns={"wh_id": "location_id"})
data_df["location_id"] = data_df["location_id"].astype(str)
data_df["product_id"] = data_df["product_id"].astype(str)
resched_df["location_id"] = resched_df["location_id"].astype(str)
resched_df["product_id"] = resched_df["product_id"].astype(str)

merged = data_df.merge(resched_df, on=["location_id", "product_id"], how="left")
merged["resched_count"] = merged["resched_count"].fillna(0)
merged["total_inbound"] = merged["total_inbound"].fillna(1)

# ---- Force numeric types BEFORE computation ----
for col in ["lead_time", "lead_time_std", "avg_demand", "std_demand", "resched_count", "total_inbound", "doi_policy"]:
    if col in merged.columns:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

# ---- Compute Final DOI ----
def compute_doi(row):
    try:
        base_doi = row["doi_policy"]
        pareto = str(row.get("pareto", "")).strip()
        cleaned_pareto = pareto if pareto in ["X", "A", "B"] else "C"
        demand_type = row.get("demand_type", "")
        product_type = row.get("product_type_name", "")

        apply_logic = (
            cleaned_pareto in selected_pareto and
            demand_type in selected_demand and
            product_type in selected_product_types
        )

        if not apply_logic:
            return round(base_doi, 2)

        safety = (
            Z * np.sqrt((row["lead_time_std"] ** 2) + (row["lead_time"] ** 2) * (row["std_demand"] / row["avg_demand"]) ** 2) * ks
            if include_safety else 0
        )
        resched = (
            kr * row["lead_time"] * (row["resched_count"] / row["total_inbound"])
            if include_reschedule else 0
        )
        pareto_val = kp * pareto_weight.get(cleaned_pareto, 0)
        multiplier = product_type_scaler.get(product_type, 1.0)

        return round(0.7 * (base_doi + safety + resched + pareto_val) * multiplier, 2)
    except Exception as e:
        st.warning(f"Error computing DOI for row: {e}")
        return base_doi

# Apply Computation
merged["final_doi"] = merged.apply(compute_doi, axis=1)

# ---- Output Section ----
st.subheader("📊 Final DOI Table")
preview_cols = ["location_id", "product_id", "product_type_name", "pareto", "demand_type", "doi_policy", "final_doi"]
available_cols = [col for col in preview_cols if col in merged.columns]
st.dataframe(merged[available_cols], use_container_width=True)

st.download_button("📥 Download Refined DOI CSV", merged.to_csv(index=False), file_name="refined_doi_output.csv")


