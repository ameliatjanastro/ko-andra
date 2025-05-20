import streamlit as st
import pandas as pd

st.title("ForecastSTEP 3 - Convert Hub Forecast to WH Forecast")

# Step 1: Upload files
forecast_file = st.file_uploader("Upload Forecast File (Excel)", type=["xlsx", "xls"])
hub_map_file = st.file_uploader("Upload Hub-WH Mapping File (CSV)", type="csv")
split_sku_file = st.file_uploader("Upload Split SKU List File (CSV)", type="csv")

if forecast_file and hub_map_file and split_sku_file:
    # Load the files
    forecast_df = pd.read_excel(forecast_file)
    hub_wh_map_df = pd.read_csv(hub_map_file)
    split_sku_df = pd.read_csv(split_sku_file)

    # Ensure column names match expected structure
    split_sku_df.columns = [col.lower() for col in split_sku_df.columns]
    if 'product_id' not in split_sku_df.columns:
        st.error("The split SKU list file must contain a 'product_id' column.")
    else:
        # Step 2: Mark SKUs to split
        forecast_df['Split_SKU'] = forecast_df['Product ID'].isin(split_sku_df['product_id'])

        # Step 3: Merge split SKUs with WH mapping
        split_df = forecast_df[forecast_df['Split_SKU']].merge(
            hub_wh_map_df, on='Hub ID', how='left'
        )
        st.write("Columns in split_df:", split_df.columns.tolist())
        # Step 4: Assign WH ID = 160 for non-split SKUs
        nonsplit_df = forecast_df[~forecast_df['Split_SKU']].copy()
        nonsplit_df['WH ID'] = 160

        # Step 5: Combine
        combined_df = pd.concat([
            split_df[['Date', 'Product ID', 'Product', 'WH ID', 'Forecast STEP 3']],
            nonsplit_df[['Date', 'Product ID', 'Product', 'WH ID', 'Forecast STEP 3']]
        ])

        # Step 6: Aggregate forecast by Date, Product ID, WH
        final_df = combined_df.groupby(
            ['Date', 'Product ID', 'Product', 'WH ID'],
            as_index=False
        )['ForecastSTEP 3'].sum()

        st.success("Forecast conversion successful!")
        st.dataframe(final_df)

        # Download output
        csv_output = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Forecast by WH (CSV)", csv_output, "ForecastSTEP3_by_WH.csv", "text/csv")

