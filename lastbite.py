import streamlit as st
import pandas as pd
import numpy as np

# Custom CSS styling
st.markdown("""
    <style>
    html, body, #root, .main { zoom: 90%; }
    .small-font h4 { font-size: 14px !important; margin-bottom: 4px !important; margin-top: 8px !important; }
    .small-font p, .small-font span, .small-font div { font-size: 12px !important; }
    div[data-testid="metric-container"] > div { font-size: 14px !important; line-height: 1.2 !important; }
    div[data-testid="metric-container"] { padding-bottom: 4px !important; }
    body { overflow: hidden !important; }
    ::-webkit-scrollbar { display: none; }
    </style>
""", unsafe_allow_html=True)

st.subheader("Last Bite Calculator")

with st.expander("ℹ️ How to Use This Calculator"):
    st.markdown("""
    **Welcome to the Last Bite Calculator!**
    
    This tool helps identify whether we should **add or reduce stock** for a specific SKU or Brand Company by:
    
    - Highlighting SKUs currently **above or below the ideal Days of Inventory (DOI)** at the warehouse
    - Quantifying the **delta from ideal DOI** to decide on stock adjustments
    - Analyzing items flagged for reorder by the RL engine that, in reality, already have high stock (i.e., should not be reordered)
    - Identifying SKUs that we **should reduce** but are still being ordered — representing **risk of excess stock**
    - Calculating potential **holding cost impact** and required sales to justify excess
    
    The goal is to ensure we stay aligned with our **ideal DOI targets** and avoid **unnecessary overstocking** by challenging current reorder logic.
    

    ### 🔍 Steps:
    1. Choose `SKU` or `Brand Company` analysis mode.
    2. Select SKU or Brand Company from the dropdown.
    3. Input the **Ideal DOI**.
    4. Click **Calculate**.
    """)

# --- Data Sources ---
SOH_CSV_URL = "https://docs.google.com/spreadsheets/d/1AdgfuvN_JrKNYKL6NXe9lX_Cd86o5u_2sr71SZIiOz4/export?format=csv&gid=251919600"
FC_CSV_URL = "https://raw.githubusercontent.com/ameliatjanastro/ko-andra/main/sales.csv"
HOLDING_COST_CSV_URL = "https://raw.githubusercontent.com/ameliatjanastro/ko-andra/main/occupancy.csv"

# Load and prepare data
try:
    soh_df = pd.read_csv(SOH_CSV_URL)
    fc_df = pd.read_csv(FC_CSV_URL)
    holding_df = pd.read_csv(HOLDING_COST_CSV_URL)

    soh_df.columns = soh_df.columns.str.strip().str.lower()
    fc_df.columns = fc_df.columns.str.strip().str.lower()
    holding_df.columns = holding_df.columns.str.strip().str.lower()

    soh_df.dropna(subset=['product id'], inplace=True)
    holding_df.dropna(subset=['product id'], inplace=True)

    df = soh_df.merge(
        fc_df[['product id', 'forecast daily']],
        on='product id'
    ).merge(
        holding_df[['product id', 'product name', 'holding_cost', 'brand company','cogs']],
        on='product id'
    )
    df.drop_duplicates(inplace=True)

    df.rename(columns={
        'sum of stock': 'soh',
        'forecast daily': 'forecast_daily',
        'holding_cost': 'holding_cost_monthly',
    }, inplace=True)

    def adjust_forecast(row):
        if row['location id'] in [40, 772]:
            if row['location id'] == 772:
                return row['forecast_daily'] * 1
            elif row['location id'] == 40:
                return row['forecast_daily'] * 0.6
        elif row['location id'] in [160, 796]:
            return row['forecast_daily'] * 0.5
        elif row['location id'] == 661:
            return row['forecast_daily']  # no change
        else:
            return 0  # if unknown location_id

    df['forecast_daily'] = df.apply(adjust_forecast, axis=1)

    df['soh'] = pd.to_numeric(df['soh'], errors='coerce')
    df['forecast_daily'] = pd.to_numeric(df['forecast_daily'], errors='coerce').replace(0, np.nan)
    df['holding_cost_monthly'] = pd.to_numeric(df['holding_cost_monthly'], errors='coerce')
    df['doi_current'] = df['soh'] / df['forecast_daily']

except Exception as e:
    st.error(f"❌ Data loading error: {e}")
    st.stop()

# Analysis mode
analysis_level = st.selectbox("Choose Analysis Level", ["SKU", "Brand Company"])

if analysis_level == "SKU":
    df['sku_display'] = df['product id'].astype(str) + ' - ' + df['product name']
    sku_display_to_id = dict(zip(df['sku_display'], df['product id']))
    selected_display = st.selectbox("Select SKU", sorted(df['sku_display'].unique()))
    selected_sku = sku_display_to_id[selected_display]

    valid_locs = df[(df['product id'] == selected_sku) & (df['soh'] > 0)]['location id'].unique()
    if len(valid_locs) == 0:
        st.warning("No stock > 0 for this SKU.")
        st.stop()

    selected_location = st.selectbox("Select Location", valid_locs)

    with st.form("sku_form"):
        doi_ideal = st.number_input("Enter Ideal DOI (days)", min_value=1.0, value=30.0, step=0.1)
        submitted = st.form_submit_button("Calculate")

    if submitted:
        working_df = df[(df['product id'] == selected_sku) & (df['location id'] == selected_location)].copy()
        working_df['doi_ideal'] = doi_ideal
        working_df['doi_diff'] = working_df['doi_current'] - working_df['doi_ideal']

        working_df['additional_qty_pcs_reduce'] = working_df.apply(
            lambda row: max(row['forecast_daily'] * row['doi_diff'], 0), axis=1)
        working_df['additional_sales_value_reduce'] = working_df['additional_qty_pcs_reduce'] * working_df['cogs']
        working_df['additional_qty_pcs_increase'] = working_df.apply(
            lambda row: max(row['forecast_daily'] * (-row['doi_diff']), 0), axis=1)
        working_df['additional_order_value'] = working_df['additional_qty_pcs_increase'] * working_df['cogs']
        working_df['additional_annual_holding_cost'] = working_df['additional_qty_pcs_increase'] * working_df['holding_cost_monthly'] * 12
        

        working_df['additional_qty_pcs_reduce_fmt'] = working_df['additional_qty_pcs_reduce'].apply(lambda x: f"{int(x):,}" if x > 0 else "-")
        working_df['additional_sales_value_reduce_fmt'] = working_df['additional_sales_value_reduce'].apply(lambda x: f"{int(x):,}" if x > 0 else "-")
        working_df['additional_qty_pcs_increase_fmt'] = working_df['additional_qty_pcs_increase'].apply(lambda x: f"{int(x):,}" if x > 0 else "-")
        working_df['additional_order_value_fmt'] = working_df['additional_order_value'].apply(lambda x: f"{int(x):,}" if x > 0 else "-")
        working_df['additional_annual_holding_cost_fmt'] = working_df['additional_annual_holding_cost'].apply(lambda x: f"{int(x):,}" if x > 0 else "-")

        for _, row in working_df.iterrows():
            st.markdown(f'<div class="small-font"><h4>🧾 <b>Product ID: {row["product id"]}</b></h4></div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("WH ID", f"{int(row['location id'])}")
                st.metric("Current Stock (SOH)", f"{int(row['soh'])}")
                st.metric("Forecast Daily", f"{row['forecast_daily']:.2f}")
                st.metric("DOI - Current", f"{row['doi_current']:.1f} days")
                st.metric("DOI - Ideal", f"{row['doi_ideal']:.1f} days")
                st.metric("Additional Qty to Reduce (pcs)", row['additional_qty_pcs_reduce_fmt'])
                st.metric("Additional Excess Qty in Value", row['additional_sales_value_reduce_fmt'])
            with col2:
                st.metric("Additional Qty to Increase (pcs)", row['additional_qty_pcs_increase_fmt'])
                st.metric("Additional Order Value", row['additional_order_value_fmt'])
                st.metric("Additional Annual Holding Cost ↑", row['additional_annual_holding_cost_fmt'])
                
            st.divider()
                
            # Delta Calculation for SKU
            qty_increase = row['additional_qty_pcs_increase']
            qty_reduce = row['additional_qty_pcs_reduce']
            value_increase = row['additional_order_value']
            value_reduce = row['additional_sales_value_reduce']
    
            delta_qty = qty_increase - qty_reduce
            delta_value = value_increase - value_reduce
    
            if delta_qty > 0:
                verdict_qty = f"📦 Need to INCREASE stock by {int(delta_qty):,} pcs"
            elif delta_qty < 0:
                verdict_qty = f"📦 Need to REDUCE stock by {int(abs(delta_qty)):,} pcs"
            else:
                verdict_qty = "📦 No stock adjustment needed"
    
            if delta_value > 0:
                verdict_value = f"💰 Net ADDITIONAL value: Rp {int(delta_value):,}"
            elif delta_value < 0:
                verdict_value = f"💰 Net REDUCTION in value: Rp {int(abs(delta_value)):,}"
            else:
                verdict_value = "💰 No value adjustment"
    
            st.markdown(f"### 📊 Verdicts for SKU")
            st.success(verdict_qty)
            st.success(verdict_value)


else:
    brand_companies = df['brand company'].dropna().unique()
    selected_brand = st.selectbox("Select Brand Company", sorted(brand_companies))

    with st.form("brand_form"):
        doi_ideal = st.number_input("Enter Ideal DOI (days)", min_value=1.0, value=30.0, step=0.1)
        submitted = st.form_submit_button("Calculate")

    if submitted:
        brand_df = df[df['brand company'] == selected_brand].copy()
        brand_df['doi_ideal'] = doi_ideal
        brand_df['doi_diff'] = brand_df['doi_current'] - brand_df['doi_ideal']

        brand_df['additional_qty_pcs_reduce'] = brand_df.apply(
            lambda row: max(row['forecast_daily'] * row['doi_diff'], 0), axis=1)
        brand_df['additional_sales_value_reduce'] = brand_df['additional_qty_pcs_reduce'] * brand_df['cogs']
        brand_df['additional_qty_pcs_increase'] = brand_df.apply(
            lambda row: max(row['forecast_daily'] * (-row['doi_diff']), 0), axis=1)
        brand_df['additional_annual_holding_cost'] = brand_df['additional_qty_pcs_increase'] * brand_df['holding_cost_monthly'] * 12
        brand_df['additional_order_value'] = brand_df['additional_qty_pcs_increase'] * brand_df['cogs']

        valid_rows = brand_df[(brand_df['forecast_daily'] > 0) & (brand_df['doi_current'].notna())]

        total_soh = valid_rows['soh'].sum()
        total_forecast = valid_rows['forecast_daily'].sum()
        total_qty_reduce = valid_rows['additional_qty_pcs_reduce'].sum()
        total_val_reduce = valid_rows['additional_sales_value_reduce'].sum()
        total_qty_increase = valid_rows['additional_qty_pcs_increase'].sum()
        total_annual_holding_cost_increase = valid_rows['additional_annual_holding_cost'].sum()
        total_order_value = valid_rows['additional_order_value'].sum()
        
        if total_forecast == 0 or total_soh == 0:
            st.warning("⚠️ Cannot compute results due to zero forecast or stock.")
        else:
            doi_current = total_soh/total_forecast
            #doi_new_reduce = (total_soh - total_qty_reduce) / total_forecast if total_qty_reduce > 0 else doi_current
            #doi_new_increase = (total_soh + total_qty_increase) / total_forecast if total_qty_increase > 0 else doi_current
            #required_sales_lift = total_qty_reduce / doi_current if doi_current > 0 else 0
            #pct_sales_increase = required_sales_lift / total_forecast if total_forecast > 0 else 0

            #verdict = '✅ Proceed' if pct_sales_increase < 2 else '❌ Not Recommended'

            st.markdown(f"<h4>📦 Summary for Brand Company: <b>{selected_brand}</b></h4>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total SOH", f"{int(total_soh)}")
                st.metric("Total Forecast Daily", f"{total_forecast:.1f}")
                st.metric("Additional Qty to Reduce (pcs)", f"{int(total_qty_reduce):,}" if total_qty_reduce > 0 else "-")
                st.metric("Additional Excess Qty in Value", f"{int(total_val_reduce):,}" if total_val_reduce > 0 else "-")
                st.metric("DOI - Current", f"{doi_current:.1f} days")
                st.metric("DOI - Ideal", f"{doi_ideal:.1f} days")
            with col2:
                st.metric("Additional Qty to Increase (pcs)", f"{int(total_qty_increase):,}" if total_qty_increase > 0 else "-")
                st.metric("Additional Order Value", f"{int(total_order_value):,}" if total_order_value > 0 else "-")
                st.metric("Additional Annual Holding Cost ↑", f"{int(total_annual_holding_cost_increase):,}" if total_annual_holding_cost_increase > 0 else "-")

            
                #st.metric("Sales Increase %", f"{pct_sales_increase*100:.1f}%" if pct_sales_increase > 0 else "-")

            #st.markdown(f"<div class='small-font'><b>Verdict:</b> {verdict}</div>", unsafe_allow_html=True)
            
            # Delta Calculation for Brand
            delta_qty = total_qty_increase - total_qty_reduce
            delta_value = total_order_value - total_val_reduce
    
            if delta_qty > 0:
                verdict_qty = f"📦 Need to INCREASE stock by {int(delta_qty):,} pcs"
            elif delta_qty < 0:
                verdict_qty = f"📦 Need to REDUCE stock by {int(abs(delta_qty)):,} pcs"
            else:
                verdict_qty = "📦 No stock adjustment needed"
    
            if delta_value > 0:
                verdict_value = f"💰 Net ADDITIONAL value: Rp {int(delta_value):,}"
            elif delta_value < 0:
                verdict_value = f"💰 Net REDUCTION in value: Rp {int(abs(delta_value)):,}"
            else:
                verdict_value = "💰 No value adjustment"
    
            st.markdown("### 📊 Verdicts for Brand Company")
            st.success(verdict_qty)
            st.success(verdict_value)


            st.markdown("### 📋 Detailed SKU-Location Table")
            brand_table = brand_df[[
                'product id', 'product name', 'location id',
                'doi_current', 'doi_ideal',
                'additional_qty_pcs_reduce', 'additional_sales_value_reduce',
                'additional_qty_pcs_increase', 'additional_order_value'
            ]].copy()

            brand_table.rename(columns={
                'product id': 'Product ID',
                'product name': 'Product Name',
                'location id': 'WH ID',
                'doi_current': 'DOI Current',
                'doi_ideal': 'DOI Ideal',
                'additional_qty_pcs_reduce': 'Qty to Reduce (pcs)',
                'additional_sales_value_reduce': 'Value to Reduce',
                'additional_qty_pcs_increase': 'Qty to Increase (pcs)',
                'additional_order_value': 'Order Value Increase',
            }, inplace=True)

            # Format numeric columns for better readability
            brand_table['DOI Current'] = brand_table['DOI Current'].round(1)
            brand_table['DOI Ideal'] = brand_table['DOI Ideal'].round(1)
            brand_table['Qty to Reduce (pcs)'] = brand_table['Qty to Reduce (pcs)'].apply(lambda x: f"{int(x):,}" if x > 0 else "-")
            brand_table['Value to Reduce'] = brand_table['Value to Reduce'].apply(lambda x: f"{int(x):,}" if x > 0 else "-")
            brand_table['Qty to Increase (pcs)'] = brand_table['Qty to Increase (pcs)'].apply(lambda x: f"{int(x):,}" if x > 0 else "-")
            brand_table['Order Value Increase'] = brand_table['Order Value Increase'].apply(lambda x: f"{int(x):,}" if x > 0 else "-")

            st.dataframe(brand_table.reset_index(drop=True), use_container_width=True)

            csv_data = brand_table.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download Table as CSV",
                data=csv_data,
                file_name=f"{selected_brand}_SKU_DOI_Adjustment.csv",
                mime='text/csv'
)










