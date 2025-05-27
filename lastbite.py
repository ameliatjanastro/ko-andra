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

    # Merge on SKU
    df = soh_df.merge(fc_df, on='Product ID').merge(holding_df, on='Product ID')

    # Rename
    df.rename(columns={
        'Sum of Stock': 'SOH',
        'Forecast Daily': 'Forecast_Daily',
        'holding_cost': 'Holding_Cost_Monthly'
    }, inplace=True)

    st.subheader("✏️ Input Extra Quantity per SKU")
    extra_qty_dict = {}
    for sku in df['sku']:
        default_val = 0
        extra_qty_dict[sku] = st.number_input(f"Extra Qty for {sku}", min_value=0, step=10, value=default_val)

    # Apply Extra Qty
    df['Extra_Qty'] = df['sku'].map(extra_qty_dict)

    # Calculations
    df['DOI_Current'] = df['SOH'] / df['Forecast_Daily']
    df['SOH_New'] = df['SOH'] + df['Extra_Qty']
    df['DOI_New'] = df['SOH_New'] / df['Forecast_Daily']
    df['Required_Sales_Increase_Units'] = df['Extra_Qty'] / df['DOI_Current']
    df['Annual_Holding_Cost_Increase'] = df['Extra_Qty'] * df['Holding_Cost_Monthly'] * 12

    # Final output
    result = df[['sku', 'SOH', 'Forecast_Daily', 'Holding_Cost_Monthly', 'Extra_Qty',
                 'DOI_Current', 'DOI_New', 'Required_Sales_Increase_Units', 'Annual_Holding_Cost_Increase']].round(2)

    st.subheader("📊 Output Table")
    st.dataframe(result)

    # Download option
    csv = result.to_csv(index=False)
    st.download_button("📥 Download Result CSV", csv, "last_bite_calculator_results.csv", "text/csv")

else:
    st.info("Please upload all 3 files: SOH, Sales Forecast, and Holding Cost.")
