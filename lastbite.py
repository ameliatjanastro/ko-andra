import streamlit as st
import pandas as pd
import numpy as np

# Zoom adjustment
st.set_page_config(layout="wide")


st.markdown(
    """
    <style>
    html, body, #root, .main {
        zoom: 85%;
    }
    .small-font {
        font-size: 13px !important;
    }
    .metric-label, .metric-value {
        font-size: 14px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Last Bite Calculator")


# Add usage guide
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
SOH_CSV_URL = "https://raw.githubusercontent.com/ameliatjanastro/ko-andra/main/soh.csv"
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
    df = soh_df.merge(fc_df, on='product id').merge(holding_df, on='product id')
    df.drop_duplicates(subset=['product id'], inplace=True)
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
st.subheader("🛠️ Modify Extra Quantity")

with st.form("extra_qty_form"):
    col1, col2 = st.columns([2, 1])

    with col1:
        selected_sku = st.selectbox("Select SKU", df['product name'].unique())

    with col2:
        extra_qty_input = st.number_input("Extra Qty", min_value=0, step=100, value=0)

    submitted = st.form_submit_button("Apply")

if submitted:
    df.loc[df['product name'] == selected_sku, 'extra_qty'] = extra_qty_input

# Recalculate based on input
df['doi_current'] = df['soh'] / df['forecast_daily']
df['soh_new'] = df['soh'] + df['extra_qty']
df['doi_new'] = df['soh_new'] / df['forecast_daily']
df['required_daily_sales_increase_units'] = df['extra_qty'] / df['doi_current']
df['annual_holding_cost_increase'] = (df['extra_qty'] * df['holding_cost_monthly'] * 12).apply(lambda x: f"{x:,.0f}")
df['extra_qty needed for cogs dicount'] = df['extra_qty']
df['%_sales_increase_raw'] = df['required_daily_sales_increase_units'] / df['forecast_daily']
df['verdict'] = df['%_sales_increase_raw'].apply(lambda x: '❌ Not Recommended' if x >= 2 else '✅ Proceed')
df['%_sales_increase'] = (df['%_sales_increase_raw'] * 100).apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else "")

# Clean and filter
df.replace([np.inf, -np.inf], np.nan, inplace=True)
df.dropna(subset=['doi_current'], inplace=True)

# Result table
result = df[['product id', 'product name', 'soh', 'forecast_daily', 'extra_qty needed for cogs dicount',
             'doi_current', 'doi_new', 'required_daily_sales_increase_units', '%_sales_increase',
             'annual_holding_cost_increase', 'verdict']].copy()

modified_result = result[result['extra_qty needed for cogs dicount'] > 0]


if not modified_result.empty:
    for _, row in modified_result.iterrows():
        st.markdown(f"#### 🧾 Results for: **{row['product name']}** (Product ID: `{row['product id']}`)")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Current Stock on Hand (SOH)", f"{int(row['soh'])}")
            st.metric("Forecast Daily Sales", f"{row['forecast_daily']:.2f}")
            st.metric("Extra Qty fo COGS discount", f"{int(row['extra_qty needed for cogs dicount'])}")
            st.metric("Required Daily Sales Increase", f"{row['required_daily_sales_increase_units']:.1f}")
        with col2:
            st.metric("DOI - Current", f"{row['doi_current']:.1f} days")
            st.metric("DOI - New", f"{row['doi_new']:.1f} days")
            st.metric("Annual Holding Cost ↑", f"{row['annual_holding_cost_increase']}")
            st.metric("Sales Increase % Needed", row['%_sales_increase'])

        st.markdown(f"####**Verdict**: {row['verdict']}")
        st.divider()
else:
    st.info("No SKUs were modified. Use the form above to enter an `Extra Qty`.")

