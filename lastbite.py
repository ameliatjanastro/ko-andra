import streamlit as st
import pandas as pd
import numpy as np

# Page layout
st.set_page_config(layout="wide")

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
        holding_df[['product id', 'product name', 'holding_cost', 'brand company']],
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
df['extra_qty'] = 0

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
        extra_qty_input = st.number_input("Extra Qty needed for COGS discount", min_value=0, step=100, value=0)
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
        extra_qty_input = st.number_input("Extra Qty to test for Brand Company", min_value=0, step=100, value=0)
        submitted = st.form_submit_button("Calculate")

    if submitted:
        df.loc[df['brand company'] == selected_brand, 'extra_qty'] = extra_qty_input

# --- Recalculate ---
df['total_forecast'] = df.groupby(['product id', 'location id'])['forecast_daily'].transform('sum')
df['forecast_ratio'] = df['forecast_daily'] / df['total_forecast'].replace(0, 1)
df['extra_qty_allocated'] = df['extra_qty'] * df['forecast_ratio']
df['doi_current'] = df['soh'] / df['forecast_daily']
df['soh_new'] = df['soh'] + df['extra_qty_allocated']
df['doi_new'] = df['soh_new'] / df['forecast_daily']
df['required_daily_sales_increase_units'] = df['extra_qty_allocated'] / df['doi_current']
df['annual_holding_cost_increase'] = (df['extra_qty_allocated'] * df['holding_cost_monthly'] * 12).apply(lambda x: f"{x:,.0f}")
df['%_sales_increase_raw'] = df['required_daily_sales_increase_units'] / df['forecast_daily']
df['%_sales_increase'] = (df['%_sales_increase_raw'] * 100).apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else "")
df['verdict'] = df['%_sales_increase_raw'].apply(lambda x: '❌ Not Recommended' if x >= 2 else '✅ Proceed')
df.replace([np.inf, -np.inf], np.nan, inplace=True)
df.dropna(subset=['doi_current'], inplace=True)

# --- Show results ---
if analysis_level == "SKU":
    modified_result = df[df['extra_qty'] > 0]
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
                st.metric("Extra Qty", f"{int(row['extra_qty'])}")
                st.metric("Required Sales ↑ (pcs)", f"{row['required_daily_sales_increase_units']:.0f}")
            with col2:
                st.metric("DOI - Current", f"{row['doi_current']:.1f} days")
                st.metric("DOI - New", f"{row['doi_new']:.1f} days")
                st.metric("Annual Holding Cost ↑", f"{row['annual_holding_cost_increase']}")
                st.metric("Sales Increase %", row['%_sales_increase'])

            st.markdown(f'<div class="small-font"><b>Verdict:</b> {row["verdict"]}</div>', unsafe_allow_html=True)
            st.divider()
    else:
        st.info("No SKUs were modified. Use the form above to enter Extra Qty.")

else:
    brand_df = df[df['brand company'] == selected_brand]
    if not brand_df.empty:
        group = brand_df.copy()
        total_soh = group['soh'].sum()
        total_forecast = group['forecast_daily'].sum()
        total_extra = group['extra_qty'].avg()

        if total_forecast == 0 or total_soh == 0:
            st.warning("⚠️ Cannot compute results due to zero forecast or stock.")
        else:
            doi_current = total_soh / total_forecast
            soh_new = total_soh + total_extra
            doi_new = soh_new / total_forecast
            required_sales_lift = total_extra / doi_current
            pct_sales_increase = required_sales_lift / total_forecast
            holding_cost = group['holding_cost_monthly'].mean()
            annual_cost = total_extra * holding_cost * 12

            verdict = '✅ Proceed' if pct_sales_increase < 2 else '❌ Not Recommended'

            st.markdown(f"<h4>📦 Summary for Brand Company: <b>{selected_brand}</b></h4>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total SOH", f"{int(total_soh)}")
                st.metric("Total Forecast Daily", f"{total_forecast:.1f}")
                st.metric("Extra Qty", f"{int(total_extra)}")
                st.metric("Required Sales ↑ (pcs)", f"{required_sales_lift:.0f}")
            with col2:
                st.metric("DOI - Current", f"{doi_current:.1f} days")
                st.metric("DOI - New", f"{doi_new:.1f} days")
                st.metric("Annual Holding Cost ↑", f"{annual_cost:,.0f}")
                st.metric("Sales Increase %", f"{pct_sales_increase*100:.1f}%")
            st.markdown(f"<div class='small-font'><b>Verdict:</b> {verdict}</div>", unsafe_allow_html=True)
    else:
        st.info("No matching Brand Company data.")






