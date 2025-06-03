import pandas as pd
import numpy as np
import streamlit as st

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
        holding_df[['product id', 'product name', 'holding_cost', 'brand company', 'cogs']],
        on='product id'
    )
    df.drop_duplicates(inplace=True)
except KeyError as e:
    st.error(f"❌ Merge failed: {e}")
    st.stop()

# Check required column
if 'cogs' not in df.columns:
    st.error("❌ 'cogs' column not found in data. Please ensure it's included.")
    st.stop()

# Rename
df.rename(columns={
    'sum of stock': 'soh',
    'forecast daily': 'forecast_daily',
    'holding_cost': 'holding_cost_monthly',
}, inplace=True)

# Check required columns
required_columns = ['brand company', 'product id', 'location id', 'forecast_daily', 'soh', 'cogs', 'holding_cost_monthly']
missing_cols = [col for col in required_columns if col not in df.columns]
if missing_cols:
    st.error(f"❌ Missing columns in data: {missing_cols}")
else:
    # Mode selection
    mode = st.radio("Select Mode", ["Brand Company Level", "SKU Level"])

    if mode == "Brand Company Level":
        selected_brand = st.selectbox("Select Brand Company", sorted(df['brand company'].dropna().unique()))

        with st.form("brand_form"):
            extra_qty_input = st.number_input("Extra Qty to test for Brand Company", min_value=0, step=100, value=0)
            submitted = st.form_submit_button("Calculate for Brand Company")

        if submitted:
            brand_df = df[df['brand company'] == selected_brand].copy()

            brand_df['total_forecast'] = brand_df.groupby(['product id', 'location id'])['forecast_daily'].transform('sum')
            brand_df['forecast_ratio'] = brand_df['forecast_daily'] / brand_df['total_forecast'].replace(0, 1)
            brand_df['extra_qty_allocated'] = extra_qty_input * brand_df['forecast_ratio']
            brand_df['extra_qty_value'] = brand_df['extra_qty_allocated'] * brand_df['cogs']
            brand_df['doi_current'] = brand_df['soh'] / brand_df['forecast_daily'].replace(0, np.nan)
            brand_df['soh_new'] = brand_df['soh'] + brand_df['extra_qty_allocated']
            brand_df['doi_new'] = brand_df['soh_new'] / brand_df['forecast_daily'].replace(0, np.nan)
            brand_df['required_daily_sales_increase_units'] = brand_df['extra_qty_allocated'] / brand_df['doi_current'].replace(0, np.nan)
            brand_df['annual_holding_cost_increase'] = (brand_df['extra_qty_allocated'] * brand_df['holding_cost_monthly'] * 12)
            brand_df['%_sales_increase_raw'] = brand_df['required_daily_sales_increase_units'] / brand_df['forecast_daily'].replace(0, np.nan)
            brand_df['%_sales_increase'] = brand_df['%_sales_increase_raw'].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "")
            brand_df['verdict'] = brand_df['%_sales_increase_raw'].apply(lambda x: '❌ Not Recommended' if x >= 2 else '✅ Proceed')
            brand_df.replace([np.inf, -np.inf], np.nan, inplace=True)
            brand_df.dropna(subset=['doi_current'], inplace=True)

            total_extra_value = brand_df['extra_qty_value'].sum()
            st.markdown(f"### 💰 Total Extra Inventory Value for {selected_brand}: Rp {total_extra_value:,.0f}")
            st.dataframe(brand_df[[
                'product id', 'location id', 'forecast_daily', 'soh', 'cogs',
                'extra_qty_allocated', 'extra_qty_value',
                'doi_current', 'doi_new',
                'required_daily_sales_increase_units',
                'annual_holding_cost_increase',
                '%_sales_increase', 'verdict'
            ]])

    elif mode == "SKU Level":
        selected_sku = st.selectbox("Select Product ID", sorted(df['product id'].dropna().unique()))
        selected_loc = st.selectbox("Select Location ID", sorted(df['location id'].dropna().unique()))

        with st.form("sku_form"):
            extra_qty_sku = st.number_input("Extra Qty to test for SKU", min_value=0, step=10, value=0)
            submitted = st.form_submit_button("Calculate for SKU")

        if submitted:
            sku_df = df[(df['product id'] == selected_sku) & (df['location id'] == selected_loc)].copy()

            if sku_df.empty:
                st.warning("⚠️ No matching data found for selected SKU and Location.")
            else:
                sku_df['extra_qty_allocated'] = extra_qty_sku
                sku_df['extra_qty_value'] = sku_df['extra_qty_allocated'] * sku_df['cogs']
                sku_df['doi_current'] = sku_df['soh'] / sku_df['forecast_daily'].replace(0, np.nan)
                sku_df['soh_new'] = sku_df['soh'] + sku_df['extra_qty_allocated']
                sku_df['doi_new'] = sku_df['soh_new'] / sku_df['forecast_daily'].replace(0, np.nan)
                sku_df['required_daily_sales_increase_units'] = sku_df['extra_qty_allocated'] / sku_df['doi_current'].replace(0, np.nan)
                sku_df['annual_holding_cost_increase'] = (sku_df['extra_qty_allocated'] * sku_df['holding_cost_monthly'] * 12)
                sku_df['%_sales_increase_raw'] = sku_df['required_daily_sales_increase_units'] / sku_df['forecast_daily'].replace(0, np.nan)
                sku_df['%_sales_increase'] = sku_df['%_sales_increase_raw'].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "")
                sku_df['verdict'] = sku_df['%_sales_increase_raw'].apply(lambda x: '❌ Not Recommended' if x >= 2 else '✅ Proceed')
                sku_df.replace([np.inf, -np.inf], np.nan, inplace=True)
                sku_df.dropna(subset=['doi_current'], inplace=True)

                total_extra_value = sku_df['extra_qty_value'].sum()
                st.markdown(f"### 💰 Total Extra Inventory Value for SKU: Rp {total_extra_value:,.0f}")
                st.dataframe(sku_df[[
                    'product id', 'location id', 'forecast_daily', 'soh', 'cogs',
                    'extra_qty_allocated', 'extra_qty_value',
                    'doi_current', 'doi_new',
                    'required_daily_sales_increase_units',
                    'annual_holding_cost_increase',
                    '%_sales_increase', 'verdict'
                ]])


# --- Show results ---
if mode == "SKU Level":
    modified_result = df[df['extra_qty'] > 0].copy()
    if not modified_result.empty:
        # Tag highest forecast only if there are duplicates
        modified_result['forecast_label'] = modified_result.groupby(
            ['product id', 'location id']
        )['forecast_daily'].transform(
            lambda x: [' (if there\'s campaign)' if v == x.max() and len(x) > 1 else '' for v in x]
        )

        for _, row in modified_result.iterrows():
            label = row['forecast_label']
            st.markdown(f'<div class="small-font"><h4>🧾 <b>Product ID: {row["product id"]}</b>{label}</h4></div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("WH ID", f"{int(row['location id'])}")
                st.metric("Current Stock (SOH)", f"{int(row['soh'])}")
                st.metric("Forecast Daily", f"{row['forecast_daily']:.2f}")
                st.metric("Extra Qty", f"{int(row['extra_qty'])}")
                st.metric("Extra Qty Value", f"{int(row['extra_qty_value'])}")
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

else:  # Brand Company level
    brand_df = df[(df['brand company'] == selected_brand) & (df['extra_qty'] > 0)].copy()
    if not brand_df.empty:
        total_soh = brand_df['soh'].sum()
        total_forecast = brand_df['forecast_daily'].sum()
        total_extra = brand_df['extra_qty'].min()
        total_extra_qty_value = brand_df['extra_qty_value'].min()

        if total_forecast == 0 or total_soh == 0:
            st.warning("⚠️ Cannot compute results due to zero forecast or stock.")
        else:
            doi_current = total_soh / total_forecast
            soh_new = total_soh + total_extra
            doi_new = soh_new / total_forecast
            required_sales_lift = total_extra / doi_current
            pct_sales_increase = required_sales_lift / total_forecast
            holding_cost = brand_df['holding_cost_monthly'].mean()
            annual_cost = total_extra * holding_cost * 12

            verdict = '✅ Proceed' if pct_sales_increase < 0.02 else '❌ Not Recommended'

            st.markdown(f"<h4>📦 Summary for Brand Company: <b>{selected_brand}</b></h4>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total SOH", f"{int(total_soh)}")
                st.metric("Total Forecast Daily", f"{total_forecast:.1f}")
                st.metric("Extra Qty", f"{int(total_extra)}")
                st.metric("Extra Qty Value", f"{int(total_extra_qty_value)}")
                st.metric("Required Sales ↑ (pcs)", f"{required_sales_lift:.0f}")
            with col2:
                st.metric("DOI - Current", f"{doi_current:.1f} days")
                st.metric("DOI - New", f"{doi_new:.1f} days")
                st.metric("Annual Holding Cost ↑", f"{annual_cost:,.0f}")
                st.metric("Sales Increase %", f"{pct_sales_increase*100:.1f}%")

            st.markdown(f"<div class='small-font'><b>Verdict:</b> {verdict}</div>", unsafe_allow_html=True)
    else:
        st.info("No matching Brand Company data.")






