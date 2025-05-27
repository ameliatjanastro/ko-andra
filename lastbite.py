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

    st.subheader("✏️ Select SKU to Edit Extra Quantity")

    # Select one SKU from the list
    selected_sku = st.selectbox("Choose SKU to edit", df['sku'].unique())
    
    # Input extra quantity for the selected SKU only
    extra_qty = st.number_input(f"Extra Qty for {selected_sku}", min_value=0, step=100, value=0)
    
    # Create a dictionary with zero extra_qty for all SKUs except the selected one
    extra_qty_dict = {sku: 0 for sku in df['sku']}
    extra_qty_dict[selected_sku] = extra_qty
    
    # Apply Extra Qty
    df['extra_qty'] = df['sku'].map(extra_qty_dict)

    df['soh'] = pd.to_numeric(df['soh'], errors='coerce')
    df['forecast_daily'] = pd.to_numeric(df['forecast_daily'], errors='coerce')
    
    # Optionally fill or drop NaNs — here we replace NaN with 0 or a small number to avoid division by zero
    df['soh'] = df['soh'].fillna(0)
    df['forecast_daily'] = df['forecast_daily'].fillna(0.0001)  # avoid division by zero

    

    # Calculations
    df['doi_current'] = df['soh'] / df['forecast_daily']
    df['soh_new'] = df['soh'] + df['extra_qty']
    df['doi_new'] = df['soh_new'] / df['forecast_daily']
    df['required_sales_increase_units per day'] = df['extra_qty'] / df['doi_current']
    df['annual_holding_cost_increase'] = df['extra_qty'] * df['holding_cost_monthly'] * 12

    # Final output with filter for modified SKUs only
    result = df[['sku', 'soh', 'forecast_daily', 'holding_cost_monthly', 'extra_qty',
                 'doi_current', 'doi_new', 'required_sales_increase_units', 'annual_holding_cost_increase']].round(2)
    
    # Show only rows where extra quantity > 0
    modified_result = result[result['extra_qty'] > 0]
    
    st.subheader("📊 Output Table (Modified SKUs Only)")
    st.dataframe(modified_result)

    # Download option
    csv = result.to_csv(index=False)
    st.download_button("📥 Download Result CSV", csv, "last_bite_calculator_results.csv", "text/csv")

else:
    st.info("Please upload all 3 files: SOH, Sales Forecast, and Holding Cost.")
