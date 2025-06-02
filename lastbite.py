import streamlit as st
import pandas as pd
import numpy as np

# Page config with wide layout
# st.set_page_config(layout="wide")

# Custom CSS: zoom out, and smaller fonts for results
st.markdown(
    """
    <style>
    html, body, #root, .main {
        zoom: 90%;
    }
    /* Smaller fonts for results */
    .small-font h4 {
        font-size: 14px !important;
        margin-bottom: 4px !important;
        margin-top: 8px !important;
    }
    .small-font p, .small-font span, .small-font div {
        font-size: 12px !important;
    }
    /* Reduce metric font size */
    div[data-testid="metric-container"] > div {
        font-size: 14px !important;
        line-height: 1.2 !important;
    }
    /* Reduce space between metrics */
    div[data-testid="metric-container"] {
        padding-bottom: 4px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.markdown(
    """
    <style>
    /* Disable vertical and horizontal scrolling */
    body {
        overflow: hidden !important;
    }
    /* Optional: Hide scrollbars (if they still appear) */
    ::-webkit-scrollbar {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.subheader("Last Bite Calculator")

# Usage guide expander
with st.expander("ℹ️ How to Use This Calculator"):
    st.markdown("""
    **Welcome to the Last Bite Calculator!**

    This tool helps you evaluate whether adding extra stock (`Extra Qty`) to a particular SKU is justifiable 
    from a financial and operational perspective. It estimates the impact on:
    
    - **Days of Inventory (DOI)** before and after the additional stock.
    - **Required sales increase** to consume the additional inventory at the same pace.
    - **Annual holding cost** of storing the added inventory.
    - **Feasibility Verdict**: Whether the increase in inventory is justifiable based on required sales increase.

    ### 📘 How to Use:
    1. **Select a SKU** from the dropdown.
    2. **Input Extra Qty** you’re considering adding.
    3. Click **Apply** to calculate.
    4. See the results in the table below.

    ### 🔎 Verdict Logic:
    - If the required sales increase is **more than 2x** the current forecast, it's **❌ Not Recommended**.
    - Otherwise, it's **✅ Proceed**.
    """)

# CSV URLs
SOH_CSV_URL = "https://docs.google.com/spreadsheets/d/1AdgfuvN_JrKNYKL6NXe9lX_Cd86o5u_2sr71SZIiOz4/export?format=csv&gid=251919600"
FC_CSV_URL = "https://raw.githubusercontent.com/ameliatjanastro/ko-andra/main/sales.csv"
HOLDING_COST_CSV_URL = "https://raw.githubusercontent.com/ameliatjanastro/ko-andra/main/occupancy.csv"

# Load CSVs from GitHub
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

# Clean data
soh_df.dropna(subset=['product id'], inplace=True)
fc_df.dropna(subset=['product id'], inplace=True)
holding_df.dropna(subset=['product id'], inplace=True)

# Merge data
try:
    df = soh_df.merge(fc_df[['product id', 'forecast daily']], on='product id').merge(holding_df[['product id', 'product name', 'holding_cost']], on='product id')
    #st.write(df.columns)
    df.drop_duplicates(inplace=True)
    #st.dataframe(df.head())

except KeyError as e:
    st.error(f"❌ Merge failed: {e}")
    st.stop()

# Rename and convert columns
df.rename(columns={
    'sum of stock': 'soh',
    'forecast daily': 'forecast_daily',
    'holding_cost': 'holding_cost_monthly',
    'product name': 'product name'
}, inplace=True)

df['soh'] = pd.to_numeric(df['soh'], errors='coerce')
df['forecast_daily'] = pd.to_numeric(df['forecast_daily'], errors='coerce').replace(0, np.nan)
df['holding_cost_monthly'] = pd.to_numeric(df['holding_cost_monthly'], errors='coerce')

df['extra_qty'] = 0

# Input form

# SKU selection outside the form
df['sku_display'] = df['product id'].astype(str) + ' - ' + df['product name']
sku_display_to_id = dict(zip(df['sku_display'], df['product id']))
selected_display = st.selectbox("Select SKU", sorted(df['sku_display'].unique()))
selected_sku = sku_display_to_id[selected_display]

# Filter valid locations where stock > 0
valid_locs = df[(df['product id'] == selected_sku) & (df['soh'] > 0)]['location id'].unique()
if len(valid_locs) == 0:
    st.warning("No locations with stock > 0 for this SKU.")
    st.stop()

# Location dropdown also outside the form
selected_location = st.selectbox("Select Location", valid_locs)

# Extra Qty input inside form
with st.form("extra_qty_form"):
    extra_qty_input = st.number_input("Extra Qty needed for COGS discount", min_value=0, step= 100, value=0)
    submitted = st.form_submit_button("Calculate")

# Apply input if submitted
if submitted:
    df.loc[
        (df['product id'] == selected_sku) & (df['location id'] == selected_location),
        'extra_qty'
    ] = extra_qty_input

# Step 1: Inverse allocation for extra_qty
df['inverse_ratio'] = 1 / df['forecast_daily'].replace(0, 1)
df['inverse_total'] = df.groupby(['product id', 'location id'])['inverse_ratio'].transform('sum')
df['forecast_inverse_ratio'] = df['inverse_ratio'] / df['inverse_total']
df['extra_qty_allocated'] = df['extra_qty'] * df['forecast_inverse_ratio']

# Step 2: Recalculate stock and DOI
df['doi_current'] = df['soh'] / df['forecast_daily']
df['soh_new'] = df['soh'] + df['extra_qty_allocated']
df['doi_new'] = df['soh_new'] / df['forecast_daily']
df['doi_gap'] = df['doi_new'] - df['doi_current']

# Step 3: Required daily sales increase
df['required_daily_sales_increase_units'] = np.where(
    df['doi_gap'] > 0,
    df['extra_qty_allocated'] / df['doi_gap'],
    np.nan
)

# Step 5: Annual holding cost increase for the allocated extra qty
df['annual_holding_cost_increase'] = (df['extra_qty_allocated'] * df['holding_cost_monthly'] * 12).apply(lambda x: f"{x:,.0f}")

# Step 6: Sales increase ratio per row
df['%_sales_increase_raw'] = df['required_daily_sales_increase_units'] / df['forecast_daily']

# Step 7: Verdict per row
df['verdict'] = df['%_sales_increase_raw'].apply(lambda x: '❌ Not Recommended' if x >= 2 else '✅ Proceed')

# Step 8: Format sales increase percentage
df['%_sales_increase'] = (df['%_sales_increase_raw'] * 100).apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else "")


# Clean and filter
df.replace([np.inf, -np.inf], np.nan, inplace=True)
df.dropna(subset=['doi_current'], inplace=True)

# Result table
result = df[['product id', 'location id', 'soh', 'forecast_daily', 'extra_qty',
             'doi_current', 'doi_new', 'required_daily_sales_increase_units', '%_sales_increase',
             'annual_holding_cost_increase', 'verdict']].copy()

modified_result = result[result['extra_qty'] > 0]

def custom_metric(label, value):
    st.markdown(f"""
        <div style='font-size:10pt; line-height:1.2; padding:6px 0;'>
                <b>{label}:</b> {value}
        </div>
    """, unsafe_allow_html=True)

if not modified_result.empty:

    modified_result['forecast_label'] = modified_result.groupby(
        ['product id', 'location id']
    )['forecast_daily'].transform(lambda x: [' (if there\'s campaign)' if v == x.max() and len(x) > 1 else '' for v in x])

    for _, row in modified_result.iterrows():
        label = row['forecast_label'] 
        st.markdown(
            f'<div class="small-font"><h4>🧾 <b>Product ID: {row["product id"]}</b>{label}</h4></div>',
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)
        with col1:
            st.metric("WH ID", f"{int(row['location id'])}")
            st.metric("Current Stock on Hand (SOH)", f"{int(row['soh'])}")
            st.metric("Forecast Daily Sales", f"{row['forecast_daily']:.2f}")
            st.metric("Extra Qty for COGS discount", f"{int(row['extra_qty'])}")
            st.metric("Required Daily Sales Increase (pcs)", f"{row['required_daily_sales_increase_units']:.0f}")
        with col2:
            st.metric("DOI - Current", f"{row['doi_current']:.1f} days")
            st.metric("DOI - New", f"{row['doi_new']:.1f} days")
            st.metric("Annual Holding Cost ↑", f"{row['annual_holding_cost_increase']}")
            st.metric("Sales Increase % Needed", row['%_sales_increase'])

        st.markdown(f'<div class="small-font"><b>Verdict:</b> {row["verdict"]}</div>', unsafe_allow_html=True)
        st.divider()
else:
    st.info("No SKUs were modified. Use the form above to enter an `Extra Qty`.")



