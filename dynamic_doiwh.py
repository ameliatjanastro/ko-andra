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

# ---- App Config and Title ----
st.set_page_config(page_title="Dynamic DOI Calculator", layout="wide")
st.markdown("<h1 style='font-size: 22px;'>📦 Dynamic DOI Calculator (GSheet Integrated)</h1>", unsafe_allow_html=True)

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
ks = st.sidebar.number_input("ks - Safety Scaling Factor", value=0.5, step=0.1) if include_safety else 0
kr = st.sidebar.number_input("kr - Reschedule Scaling Factor", value=0.5, step=0.1) if include_reschedule else 0
kp = st.sidebar.number_input("kp - Pareto Scaling Factor", value=0.5, step=0.1) if include_pareto else 0

pareto_weight = {"X": 0, "A": 0, "B": 0, "C": 0}
if include_pareto:
    st.sidebar.markdown("#### Pareto Weights")
    pareto_weight["X"] = st.sidebar.number_input("Weight for Pareto X", value=1.0)
    pareto_weight["A"] = st.sidebar.number_input("Weight for Pareto A", value=1.0)
    pareto_weight["B"] = st.sidebar.number_input("Weight for Pareto B", value=0.75)
    pareto_weight["C"] = st.sidebar.number_input("Weight for Pareto C (and others)", value=0.5)

product_type_scaler = {"Fresh": 1.0, "Frozen": 1.0, "Dry": 1.0}
if include_multiplier:
    st.sidebar.markdown("#### Product Type Multipliers")
    product_type_scaler["Fresh"] = st.sidebar.number_input("Fresh Multiplier", value=1.1)
    product_type_scaler["Frozen"] = st.sidebar.number_input("Frozen Multiplier", value=1.05)
    product_type_scaler["Dry"] = st.sidebar.number_input("Dry Multiplier", value=1.0)

# ---- Merge Reschedule Data ----
resched_df = resched_df.rename(columns={"wh_id": "location_id"})
data_df["location_id"] = data_df["location_id"].astype(str)
data_df["product_id"] = data_df["product_id"].astype(str)
resched_df["location_id"] = resched_df["location_id"].astype(str)
resched_df["product_id"] = resched_df["product_id"].astype(str)

merged = data_df.merge(resched_df, on=["location_id", "product_id"], how="left")
merged["resched_count"] = merged["resched_count"].fillna(0)
merged["total_inbound"] = merged["total_inbound"].fillna(1)

# ---- Convert numeric columns safely ----
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

        std_d_ratio = row["std_demand"] / row["avg_demand"] if row["avg_demand"] != 0 else 0
        safety = (
            Z * np.sqrt((row["lead_time_std"] ** 2) + (row["lead_time"] ** 2) * (std_d_ratio ** 2)) * ks
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

# ---- Apply Computation ----
merged["final_doi"] = merged.apply(compute_doi, axis=1)

# ---- Output Section ----
st.markdown("<style>div[data-testid='stDataFrame'] table { font-size: 12px !important; }</style>", unsafe_allow_html=True)
st.subheader("📊 Final DOI Table")

highlight_toggle = st.checkbox("Highlight rows with DOI change", value=True)

preview_cols = ["location_id", "product_id", "product_type_name", "pareto", "demand_type", "doi_policy", "final_doi"]
preview_df = merged[preview_cols].fillna("-")

def highlight_changed_doi(row):
    return ["background-color: #ffe599"] * len(row) if row["final_doi"] != round(row["doi_policy"], 2) else [""] * len(row)

if highlight_toggle:
    styled_df = preview_df.style.apply(highlight_changed_doi, axis=1)
    st.dataframe(styled_df, use_container_width=True)
else:
    st.dataframe(preview_df, use_container_width=True)

st.download_button("📥 Download Refined DOI CSV", merged.to_csv(index=False), file_name="refined_doi_output.csv")


st.download_button("📥 Download Refined DOI CSV", merged.to_csv(index=False), file_name="refined_doi_output.csv")



