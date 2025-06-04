import streamlit as st
import pandas as pd
import numpy as np

# Page layout


# Custom CSS styling
st.markdown("""
    <style>
    html, body, #root, .main {
        zoom: 90%;
    }
    .small-font h4 {
        font-size: 14px !important;
        margin-bottom: 4px !important;
        margin-top: 8px !important;
    }
    .small-font p, .small-font span, .small-font div {
        font-size: 12px !important;
    }
    div[data-testid="metric-container"] > div {
        font-size: 14px !important;
        line-height: 1.2 !important;
    }
    div[data-testid="metric-container"] {
        padding-bottom: 4px !important;
    }
    body { overflow: hidden !important; }
    ::-webkit-scrollbar { display: none; }
    </style>
""", unsafe_allow_html=True)

st.subheader("Last Bite Calculator")

with st.expander("ℹ️ How to Use This Calculator"):
    st.markdown("""
    **Welcome to the Last Bite Calculator!**

    This tool helps evaluate whether adding extra stock to a SKU or Brand Company is justifiable by:
    - Calculating impact on DOI (Days of Inventory)
    - Estimating required sales lift to justify extra inventory
    - Showing added annual holding costs
    - Giving a clear Proceed/Reject Verdict

    ### 🔍 Steps:
    1. Choose `SKU` or `Brand Company` analysis mode.
    2. Select SKU or Brand Company from the dropdown.
    3. Input the **Extra Qty**.
    4. Click **Calculate**.
    """)

# --- Data Sources ---
SOH_CSV_URL = "https://docs.google.com/spreadsheets/d/1AdgfuvN_JrKNYKL6NXe9lX_Cd86o5u_2sr71SZIiOz4/export?format=csv&gid=251919600"
FC_CSV_URL = "https://raw.githubusercontent.com/ameliatjanastro/ko-andra/main/sales.csv"
HOLDING_COST_CSV_URL = "https://raw.githubusercontent.com/ameliatjanastro/ko-andra/main/occupancy.csv"

# Load data
try:
    soh_df = pd.read_csv(SOH_CSV_URL)
    fc_df = pd.read_csv(FC_CSV_URL)
    holding_df = pd.read_csv(HOLDING_COST_CSV_URL)

    soh_df.columns = soh_df.columns.str.strip().str.lower()
    fc_df.columns = fc_df.columns.str.strip().str.lower()
    holding_df.columns = holding_df.columns.str.strip().str.lower()
except Exception as e:
    st.error(f"❌ Failed to load CSVs from GitHub: {e}")
    st.stop()

# Drop missing product IDs
soh_df.dropna(subset=['product id'], inplace=True)
holding_df.dropna(subset=['product id'], inplace=True)

# Merge
try:
    df = soh_df.merge(
        fc_df[['product id', 'forecast daily']],
        on='product id'
    ).merge(
        holding_df[['product id', 'product name', 'holding_cost', 'brand company','cogs']],
        on='product id'
    )
    df.drop_duplicates(inplace=True)
except KeyError as e:
    st.error(f"❌ Merge failed: {e}")
    st.stop()

# Rename
df.rename(columns={
    'sum of stock': 'soh',
    'forecast daily': 'forecast_daily',
    'holding_cost': 'holding_cost_monthly',
}, inplace=True)

# Convert types
df['soh'] = pd.to_numeric(df['soh'], errors='coerce')
df['forecast_daily'] = pd.to_numeric(df['forecast_daily'], errors='coerce').replace(0, np.nan)
df['holding_cost_monthly'] = pd.to_numeric(df['holding_cost_monthly'], errors='coerce')
df['doi_current'] = df['soh'] / df['forecast_daily']
df['doi_ideal'] = 14

# --- User selects analysis level ---
analysis_level = st.selectbox("Choose Analysis Level", ["SKU", "Brand Company"])

# --- SKU LEVEL ---
if analysis_level == "SKU":
    df['sku_display'] = df['product id'].astype(str) + ' - ' + df['product name']
    sku_display_to_id = dict(zip(df['sku_display'], df['product id']))
    selected_display = st.selectbox("Select SKU", sorted(df['sku_display'].unique()))
    selected_sku = sku_display_to_id[selected_display]

    valid_locs = df[(df['product id'] == selected_sku) & (df['soh'] > 0)]['location id'].unique()
    if len(valid_locs) == 0:
        st.warning("No locations with stock > 0 for this SKU.")
        st.stop()

    selected_location = st.selectbox("Select Location", valid_locs)

    with st.form("sku_form"):
        doi_ideal = st.number_input("Enter Ideal DOI (days)", min_value=1.0, value=30.0, step=0.1)
        submitted = st.form_submit_button("Calculate")

    if submitted:
        df.loc[
            (df['product id'] == selected_sku) & (df['location id'] == selected_location),
            'extra_qty'
        ] = extra_qty_input

# --- BRAND COMPANY LEVEL ---
else:
    brand_companies = df['brand company'].dropna().unique()
    selected_brand = st.selectbox("Select Brand Company", sorted(brand_companies))


    with st.form("brand_form"):
        doi_ideal = st.number_input("Enter Ideal DOI (days)", min_value=1.0, value=30.0, step=0.1)
        submitted = st.form_submit_button("Calculate")
    if submitted:
        df.loc[df['brand company'] == selected_brand, 'extra_qty'] = extra_qty_input

df['doi_diff'] = df['doi_current'] - df['doi_ideal']

# Additional qty to reduce (pcs) if current DOI > ideal DOI
df['additional_qty_pcs_reduce'] = df.apply(
    lambda row: max(row['forecast_daily'] * row['doi_diff'], 0) if row['doi_diff'] > 0 else 0, axis=1)

# Additional sales value (to reduce)
df['additional_sales_value_reduce'] = df['additional_qty_pcs_reduce'] * df['cogs']

# Additional qty to increase (pcs) if current DOI < ideal DOI
df['additional_qty_pcs_increase'] = df.apply(
    lambda row: max(row['forecast_daily'] * (-row['doi_diff']), 0) if row['doi_diff'] < 0 else 0, axis=1)

# Additional annual holding cost (to increase)
df['additional_annual_holding_cost'] = df['additional_qty_pcs_increase'] * df['holding_cost_monthly'] * 12

# Formatting for display
df['additional_qty_pcs_reduce_fmt'] = df['additional_qty_pcs_reduce'].apply(lambda x: f"{int(x):,}" if x > 0 else "-")
df['additional_sales_value_reduce_fmt'] = df['additional_sales_value_reduce'].apply(lambda x: f"{int(x):,}" if x > 0 else "-")
df['additional_qty_pcs_increase_fmt'] = df['additional_qty_pcs_increase'].apply(lambda x: f"{int(x):,}" if x > 0 else "-")
df['additional_annual_holding_cost_fmt'] = df['additional_annual_holding_cost'].apply(lambda x: f"{int(x):,}" if x > 0 else "-")

# Replace inf and nan values if any
df.replace([np.inf, -np.inf], np.nan, inplace=True)
df.dropna(subset=['doi_current', 'forecast_daily', 'soh', 'cogs', 'holding_cost_monthly', 'doi_ideal'], inplace=True)

# -- Display Section --

if analysis_level == "SKU":
    modified_result = df[(df['additional_qty_pcs_reduce'] > 0) | (df['additional_qty_pcs_increase'] > 0)]
    if not modified_result.empty:
        modified_result['forecast_label'] = modified_result.groupby(
            ['product id', 'location id']
        )['forecast_daily'].transform(lambda x: [' (if there\'s campaign)' if v == x.max() and len(x) > 1 else '' for v in x])

        for _, row in modified_result.iterrows():
            label = row['forecast_label']
            st.markdown(f'<div class="small-font"><h4>🧾 <b>Product ID: {row["product id"]}</b>{label}</h4></div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("WH ID", f"{int(row['location id'])}")
                st.metric("Current Stock (SOH)", f"{int(row['soh'])}")
                st.metric("Forecast Daily", f"{row['forecast_daily']:.2f}")
                st.metric("DOI - Current", f"{row['doi_current']:.1f} days")
                st.metric("DOI - Ideal", f"{row['doi_ideal']:.1f} days")

                st.metric("Additional Qty to Reduce (pcs)", row['additional_qty_pcs_reduce_fmt'])
                st.metric("Additional Sales Value ↓", row['additional_sales_value_reduce_fmt'])

            with col2:
                st.metric("Additional Qty to Increase (pcs)", row['additional_qty_pcs_increase_fmt'])
                st.metric("Additional Annual Holding Cost ↑", row['additional_annual_holding_cost_fmt'])

            st.divider()
    else:
        st.info("No SKUs need adjustment based on the DOI ideal.")

else:
    brand_df = df[df['brand company'] == selected_brand]

    total_soh = brand_df['soh'].sum()
    total_forecast = brand_df['forecast_daily'].sum()
    total_qty_reduce = brand_df['additional_qty_pcs_reduce'].sum()
    total_val_reduce = (brand_df['additional_qty_pcs_reduce'] * brand_df['cogs']).sum()

    total_qty_increase = brand_df['additional_qty_pcs_increase'].sum()
    avg_holding_cost = brand_df['holding_cost_monthly'].mean()
    total_annual_holding_cost_increase = (total_qty_increase * avg_holding_cost * 12)

    if total_forecast == 0 or total_soh == 0:
        st.warning("⚠️ Cannot compute results due to zero forecast or stock.")
    else:
        doi_current = total_soh / total_forecast
        doi_ideal_brand = doi_ideal  # adjust if needed

        doi_new_reduce = (total_soh - total_qty_reduce) / total_forecast if total_qty_reduce > 0 else doi_current
        doi_new_increase = (total_soh + total_qty_increase) / total_forecast if total_qty_increase > 0 else doi_current

        required_sales_lift = total_qty_reduce / doi_current if total_qty_reduce > 0 else 0
        pct_sales_increase = required_sales_lift / total_forecast if total_forecast > 0 else 0

        verdict = '✅ Proceed'
        if pct_sales_increase >= 2:
            verdict = '❌ Not Recommended'

        st.markdown(f"<h4>📦 Summary for Brand Company: <b>{selected_brand}</b></h4>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total SOH", f"{int(total_soh)}")
            st.metric("Total Forecast Daily", f"{total_forecast:.1f}")
            st.metric("Additional Qty to Reduce (pcs)", f"{int(total_qty_reduce)}" if total_qty_reduce > 0 else "-")
            st.metric("Additional Sales Value ↓", f"{int(total_val_reduce):,}" if total_val_reduce > 0 else "-")
            st.metric("DOI - Current", f"{doi_current:.1f} days")
            st.metric("DOI - New (Reduce)", f"{doi_new_reduce:.1f} days" if total_qty_reduce > 0 else "-")

        with col2:
            st.metric("Additional Qty to Increase (pcs)", f"{int(total_qty_increase)}" if total_qty_increase > 0 else "-")
            st.metric("Additional Annual Holding Cost ↑", f"{int(total_annual_holding_cost_increase):,}" if total_annual_holding_cost_increase > 0 else "-")
            st.metric("DOI - New (Increase)", f"{doi_new_increase:.1f} days" if total_qty_increase > 0 else "-")
            st.metric("Sales Increase %", f"{pct_sales_increase*100:.1f}%" if pct_sales_increase > 0 else "-")

        st.markdown(f"<div class='small-font'><b>Verdict:</b> {verdict}</div>", unsafe_allow_html=True)










