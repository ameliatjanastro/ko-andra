import streamlit as st
import pandas as pd
import numpy as np

# Zoom adjustment
st.markdown(
    """
    <style>
    html, body, #root, .main {
        zoom: 92%;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📦 Last Bite Calculator")

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
    3. The calculator will:
        - Recalculate inventory days (DOI).
        - Estimate required sales increase.
        - Calculate the added annual holding cost.
        - Give a **Verdict** whether to proceed or not based on the projected sales effort.
    
    The results will be shown below only if a non-zero `Extra Qty` is entered.

    ### 🔎 Verdict Logic:
    - If the required sales increase is **more than 2x** the current forecast, it's **Not Recommended**.
    - Otherwise, it's labeled as **Proceed**.

    This helps in making **data-driven decisions** for Last Bite or final push inventory campaigns.
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

# Initialize extra_qty
df['extra_qty'] = 0

# SKU selection
selected_sku = st.selectbox("Choose SKU to modify", df['product name'].unique())
extra_qty_input = st.number_input(f"Enter Extra Qty for '{selected_sku}'", min_value=0, step=100, value=0)
df.loc[df['product name'] == selected_sku, 'extra_qty'] = extra_qty_input

# Calculations
df['doi_current'] = df['soh'] / df['forecast_daily']
df['soh_new'] = df['soh'] + df['extra_qty']
df['doi_new'] = df['soh_new'] / df['forecast_daily']
df['required_daily_sales_increase_units'] = df['extra_qty'] / df['doi_current']
df['annual_holding_cost_increase'] = (df['extra_qty'] * df['holding_cost_monthly'] * 12).apply(lambda x: f"{x:,.0f}")
df['extra_qty needed for cogs dicount'] = df['extra_qty']
df['%_sales_increase_raw'] = df['required_daily_sales_increase_units'] / df['forecast_daily']

# Now, use the raw value for logic
df['verdict'] = df['%_sales_increase_raw'].apply(lambda x: 'Not Recommended' if x >= 2 else 'Proceed')

# Then, create the formatted version for display
df['%_sales_increase'] = (df['%_sales_increase_raw'] * 100).apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else "")

# Clean invalid rows
df.replace([np.inf, -np.inf], np.nan, inplace=True)
df.dropna(subset=['doi_current'], inplace=True)

# Result dataframe
result = df[['product id', 'product name', 'soh', 'forecast_daily', 'extra_qty needed for cogs dicount',
             'doi_current', 'doi_new', 'required_daily_sales_increase_units', '%_sales_increase',
             'annual_holding_cost_increase', 'verdict']].copy()

# Filter modified SKUs
modified_result = result[result['extra_qty needed for cogs dicount'] > 0]

# Output
st.subheader("📊 Output")
if not modified_result.empty:
    result_dict = modified_result.round(2).to_dict(orient="records")
    st.json(result_dict)

    for _, row in modified_result.iterrows():
        sku = row['product name']
        verdict = row['verdict']
        st.markdown(f"**{sku}**: **{verdict}**")
else:
    st.info("No SKUs were modified.")


