import streamlit as st
import pandas as pd

st.title("📦 Last Bite Calculator")

# Upload CSVs
SOH_CSV_URL = "https://raw.githubusercontent.com/ameliatjanastro/ko-andra/main/soh.csv"
FC_CSV_URL = "https://raw.githubusercontent.com/ameliatjanastro/ko-andra/main/sales.csv"
HOLDING_COST_CSV_URL = "https://raw.githubusercontent.com/ameliatjanastro/ko-andra/main/occupancy.csv"

# Load CSVs from GitHub
try:
    soh_df = pd.read_csv(SOH_CSV_URL)
    fc_df = pd.read_csv(FC_CSV_URL)
    holding_df = pd.read_csv(HOLDING_COST_CSV_URL)

    soh_df.columns = soh_df.columns.str.strip()
    fc_df.columns = fc_df.columns.str.strip()
    holding_df.columns = holding_df.columns.str.strip()
except Exception as e:
    st.error(f"❌ Failed to load CSVs from GitHub: {e}")
    st.stop()

#if soh_file and fc_file and holding_file:
    # Load data
    #soh_df = pd.read_csv(soh_file)
    #fc_df = pd.read_csv(fc_file)
    #holding_df = pd.read_csv(holding_file)

    # Standardize column names
    soh_df.columns = soh_df.columns.str.strip().str.lower()
    fc_df.columns = fc_df.columns.str.strip().str.lower()
    holding_df.columns = holding_df.columns.str.strip().str.lower()

    #st.write("🧾 SOH columns:", soh_df.columns.tolist())
    #st.write("🧾 Forecast columns:", fc_df.columns.tolist())
    #st.write("🧾 Holding cost columns:", holding_df.columns.tolist())

    # Merge using product id
    try:
        df = soh_df.merge(fc_df, on='product id').merge(holding_df, on='product id')
    except KeyError as e:
        st.error(f"❌ Merge failed: {e}")
        st.stop()

    # Rename columns for internal use
    df.rename(columns={
        'product id': 'sku',
        'sum of stock': 'soh',
        'forecast daily': 'forecast_daily',
        'holding_cost': 'holding_cost_monthly'
    }, inplace=True)

    # Coerce types
    df['soh'] = pd.to_numeric(df['soh'], errors='coerce')
    df['forecast_daily'] = pd.to_numeric(df['forecast_daily'], errors='coerce')
    df['holding_cost_monthly'] = pd.to_numeric(df['holding_cost_monthly'], errors='coerce')

    # Initialize extra qty column
    df['extra_qty'] = 0

    st.subheader("✏️ Select SKU and Input Extra Quantity")
    selected_sku = st.selectbox("Choose SKU to modify", df['product name'].unique())

    extra_qty_input = st.number_input(f"Enter Extra Qty for '{selected_sku}'", min_value=0, step=100, value=0)

    # Apply user input
    df.loc[df['product name'] == selected_sku, 'extra_qty'] = extra_qty_input

    # Perform calculations
    df['doi_current'] = df['soh'] / df['forecast_daily']
    df['soh_new'] = df['soh'] + df['extra_qty']
    df['doi_new'] = df['soh_new'] / df['forecast_daily']
    df['required_sales_increase_units'] = df['extra_qty'] / df['doi_current']
    df['annual_holding_cost_increase'] = (df['extra_qty'] * df['holding_cost_monthly'] * 12).apply(lambda x: f"{x:,.0f}")

    #st.write("🔍 Final DataFrame Columns:", df.columns.tolist())

    # Final output
    result = df[['product name', 'forecast_daily', 'extra_qty',
                 'doi_current', 'doi_new', 'required_sales_increase_units',
                 'annual_holding_cost_increase']].copy()

    # Filter only modified SKUs
    modified_result = result[result['extra_qty'] > 0]

    st.subheader("📊 Output Table (Only Modified SKUs)")
    if not modified_result.empty:
        result_dict = modified_result.round(2).to_dict(orient="records")
        st.json(result_dict)  # Pretty-prints each row as a dictionary
    
        # Still allow CSV download
        #csv = modified_result.to_csv(index=False)
        #st.download_button("📥 Download Result CSV", csv, "last_bite_calculator_results.csv", "text/csv")
    else:
        st.info("No SKUs were modified.")
#else:
    #st.info("📂 Please upload all 3 files: SOH, Sales Forecast, and Holding Cost.")

