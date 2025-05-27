import streamlit as st
import pandas as pd

st.title("📦 Last Bite Calculator")

# Upload CSVs
soh_file = st.file_uploader("Upload SOH CSV", type="csv")
fc_file = st.file_uploader("Upload Daily Sales Forecast CSV", type="csv")
holding_file = st.file_uploader("Upload Holding Cost CSV", type="csv")

if soh_file and fc_file and holding_file:
    # Load data
    soh_df = pd.read_csv(soh_file)
    fc_df = pd.read_csv(fc_file)
    holding_df = pd.read_csv(holding_file)

    # Standardize column names
    soh_df.columns = soh_df.columns.str.strip().str.lower()
    fc_df.columns = fc_df.columns.str.strip().str.lower()
    holding_df.columns = holding_df.columns.str.strip().str.lower()

    st.write("SOH columns:", soh_df.columns.tolist())
    st.write("Forecast columns:", fc_df.columns.tolist())
    st.write("Holding cost columns:", holding_df.columns.tolist())

    # Merge using product id
    df = soh_df.merge(fc_df, on='product id', how='outer').merge(holding_df, on='product id', how='outer')

    # Fill missing numeric columns with zeros (or another default)
    numeric_cols = ['sum of stock', 'forecast daily', 'holding_cost']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)


    # Rename columns for consistency
    df.rename(columns={
        'product id': 'sku',
        'sum of stock': 'soh',
        'forecast daily': 'forecast_daily',
        'holding_cost': 'holding_cost_monthly'
    }, inplace=True)

    st.subheader("✏️ Input Extra Quantity per SKU")
    extra_qty_dict = {}
    for sku in df['sku']:
        default_val = 0
        extra_qty_dict[sku] = st.number_input(f"Extra Qty for {sku}", min_value=0, step=10, value=default_val)

    # Apply Extra Qty
    df['extra_qty'] = df['sku'].map(extra_qty_dict)

    # Calculations
    df['doi_current'] = df['soh'] / df['forecast_daily']
    df['soh_new'] = df['soh'] + df['extra_qty']
    df['doi_new'] = df['soh_new'] / df['forecast_daily']
    df['required_sales_increase_units'] = df['extra_qty'] / df['doi_current']
    df['annual_holding_cost_increase'] = df['extra_qty'] * df['holding_cost_monthly'] * 12

    # Final output
    result = df[['sku', 'soh', 'forecast_daily', 'holding_cost_monthly', 'extra_qty',
                 'doi_current', 'doi_new', 'required_sales_increase_units', 'annual_holding_cost_increase']].round(2)

    st.subheader("📊 Output Table")
    st.dataframe(result)

    # Download option
    csv = result.to_csv(index=False)
    st.download_button("📥 Download Result CSV", csv, "last_bite_calculator_results.csv", "text/csv")

else:
    st.info("Please upload all 3 files: SOH, Sales Forecast, and Holding Cost.")
