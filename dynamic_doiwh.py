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
st.set_page_config(page_title="Dynamic DOI Calculator")

st.markdown("""
    <style>
    /* 1. Disable scrolling in the sidebar */
    [data-testid="stSidebar"] {
        overflow: hidden !important;
    }
    /* 2. Reduce top padding in sidebar content */
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0.5rem !important;
    }
    /* Shrink sidebar width */
    [data-testid="stSidebar"] * {
        font-size: 13px !important;
    }
    [data-testid="stSidebar"] > div {
        padding: 0.5rem 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    /* Target column blocks only inside open expanders */
    details[open] > div > div:nth-of-type(1),
    details[open] > div > div:nth-of-type(2),
    details[open] > div > div:nth-of-type(3) {
        transform: scale(0.85);
        transform-origin: center;
    label {
        font-size: 12.5px !important;
        font-weight: 600 !important;
        color: #333 !important;
        margin-bottom: 2px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='font-size: 22px;'>📦 Dynamic DOI Calculator</h1>", unsafe_allow_html=True)

# ---- Load Data ----
with st.spinner("Loading data from Google Sheets..."):
    data_df, resched_df = load_data()
    st.success("Data successfully loaded!")

# ---- Standardize Columns ----
data_df.columns = data_df.columns.str.strip().str.lower()
resched_df.columns = resched_df.columns.str.strip().str.lower()

# ---- Sidebar: Module Toggle ----
st.sidebar.header("Select DOI Components to Include")
include_safety = st.sidebar.checkbox("Demand Variability", True)
include_reschedule = st.sidebar.checkbox("Reschedule Adjustment", True)
include_pareto = st.sidebar.checkbox("Pareto Buffer", True)
include_multiplier = st.sidebar.checkbox("Product Type Buffer", True)

# ---- Sidebar: Filter Scope ----
st.sidebar.header("Apply Logic To")
selected_pareto = st.sidebar.multiselect("Pareto Classes", ["X", "A", "B", "C", "D"], default=["X", "A"])
selected_demand = st.sidebar.multiselect("Demand Types", ["Stable", "Volatile", "Moderate"], default=["Volatile"])
selected_product_types = st.sidebar.multiselect("Product Types", ["Fresh", "Frozen", "Dry"], default=["Fresh", "Frozen", "Dry"])

pareto_weight = {"X": 0, "A": 0, "B": 0, "C": 0}
product_type_scaler = {"Fresh": 1.0, "Frozen": 1.0, "Dry": 1.0}

# Move these outside the sidebar
pareto_weight = {"X": 0, "A": 0, "B": 0, "C": 0}
product_type_scaler = {"Fresh": 1.0, "Frozen": 1.0, "Dry": 1.0}

with st.expander("⚙️ Adjust Model Parameters", expanded=False):

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        Z = st.number_input("**Z-Score**", value=1.65, step=0.05, label_visibility="visible")
    with col2:
        ks = st.number_input("**ks (Demand Var)**", value=0.5, step=0.1, label_visibility="visible") if include_safety else 0
    with col3:
        kr = st.number_input("**kr (Resched)**", value=0.5, step=0.1, label_visibility="visible") if include_reschedule else 0
    with col4:
        kp = st.number_input("**kp (Pareto)**", value=0.5, step=0.1, label_visibility="visible") if include_pareto else 0

    if include_pareto:
        st.markdown("**Pareto Weights**")
        w1, w2, w3, w4 = st.columns(4)
        with w1:
            pareto_weight["X"] = st.number_input("X", value=1.0, step=0.1, label_visibility="visible")
        with w2:
            pareto_weight["A"] = st.number_input("A", value=1.0, step=0.1, label_visibility="visible")
        with w3:
            pareto_weight["B"] = st.number_input("B", value=0.75, step=0.1, label_visibility="visible")
        with w4:
            pareto_weight["C and Others"] = st.number_input("C", value=0.5, step=0.1, label_visibility="visible")
    else:
        pareto_weight = {"X": 0, "A": 0, "B": 0, "C": 0}

    if include_multiplier:
        st.markdown("**Product Type Multipliers**")
        m1, m2, m3 = st.columns(3)
        with m1:
            product_type_scaler["Fresh"] = st.number_input("Fresh", value=1.1, step=0.05, label_visibility="visible")
        with m2:
            product_type_scaler["Frozen"] = st.number_input("Frozen", value=1.05, step=0.05, label_visibility="visible")
        with m3:
            product_type_scaler["Dry"] = st.number_input("Dry", value=1.0, step=0.05, label_visibility="visible")
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
merged["location_id"] = pd.to_numeric(merged["location_id"], errors="coerce").fillna(0).astype(int)
merged["doi_policy"] = merged["doi_policy"].round(2)
merged["final_doi"] = merged["final_doi"].round(2)

show_changed_only = st.sidebar.checkbox("Show only rows with changed DOI", value=False)

# ---- Output Section ----
st.markdown("<style>div[data-testid='stDataFrame'] table { font-size: 12px !important; }</style>", unsafe_allow_html=True)
st.markdown("<h3 style='font-size:16px;'>Final DOI Table</h3>", unsafe_allow_html=True)

preview_cols = ["location_id", "product_id", "product_type_name", "pareto", "demand_type", "doi_policy", "final_doi"]

preview_df = merged[preview_cols].fillna("-")
preview_df["final_doi"] = preview_df["final_doi"].round(2)
preview_df["doi_policy"] = preview_df["doi_policy"].round(2)

if show_changed_only:
    preview_df = preview_df[merged["final_doi"] != merged["doi_policy"]]


st.dataframe(preview_df, use_container_width=True)

st.download_button("📥 Download Refined DOI CSV", merged.to_csv(index=False), file_name="refined_doi_output.csv")



