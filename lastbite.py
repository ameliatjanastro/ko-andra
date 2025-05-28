import streamlit as st
import pandas as pd
import numpy as np

st.markdown(
    """
    <style>
    /* Scale the whole app down to 95% */
    html, body, #root, .main {
        zoom: 95%;
    }
    </style>
    """,
    unsafe_allow_html=True
)


st.title("📦 Last Bite Calculator")

SOH_CSV_URL = "https://raw.githubusercontent.com/ameliatjanastro/ko-andra/main/soh.csv"
FC_CSV_URL = "https://raw.githubusercontent.com/ameliatjanastro/ko-andra/main/sales.csv"
HOLDING_COST_CSV_URL = "https://raw.githubusercontent.com/ameliatjanastro/ko-andra/main/occupancy.csv"

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

try:
    df = soh_df.merge(fc_df, on='product id').merge(holding_df, on='product id')
except KeyError as e:
    st.error(f"❌ Merge failed: {e}")
    st.stop()

df.rename(columns={
    'product id': 'sku',
    'sum of stock': 'soh',
    'forecast daily': 'forecast_daily',
    'holding_cost': 'holding_cost_monthly',
    'product name': 'product name'  # keep as is
}, inplace=True)

# Convert to numeric and handle errors
df['soh'] = pd.to_numeric(df['soh'], errors='coerce')
df['forecast_daily'] = pd.to_numeric(df['forecast_daily'], errors='coerce').replace(0, np.nan)
df['holding_cost_monthly'] = pd.to_numeric(df['holding_cost_monthly'], errors='coerce')

#st.write("Merged DataFrame preview:", df.head())
#st.write("Available SKUs:", df['product name'].unique())

df['extra_qty'] = 0

selected_sku = st.selectbox("Choose SKU to modify", df['product name'].unique())

extra_qty_input = st.number_input(f"Enter Extra Qty for '{selected_sku}'", min_value=0, step=100, value=0)
df.loc[df['product name'] == selected_sku, 'extra_qty'] = extra_qty_input

# Calculate DOI columns safely
df['doi_current'] = df['soh'] / df['forecast_daily']
df['soh_new'] = df['soh'] + df['extra_qty']
df['doi_new'] = df['soh_new'] / df['forecast_daily']
df['required_sales_increase_units'] = df['extra_qty'] / df['doi_current']
df['annual_holding_cost_increase'] = (df['extra_qty'] * df['holding_cost_monthly'] * 12).apply(lambda x: f"{x:,.0f}")
df['extra_qty needed for cogs dicount'] = df['extra_qty'] 
# Remove invalid DOI rows (where division caused NaN or inf)
df.replace([np.inf, -np.inf], np.nan, inplace=True)
df.dropna(subset=['doi_current'], inplace=True)

result = df[['product name', 'forecast_daily', 'extra_qty needed for cogs dicount',
             'doi_current', 'doi_new', 'required_sales_increase_units',
             'annual_holding_cost_increase']].copy()

modified_result = result[result['extra_qty'] > 0]

st.subheader("📊 Output ")
if not modified_result.empty:
    result_dict = modified_result.round(2).to_dict(orient="records")
    st.json(result_dict)
else:
    st.info("No SKUs were modified.")


