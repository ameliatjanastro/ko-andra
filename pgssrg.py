import streamlit as st
import pandas as pd

st.title("ForecastSTEP 3 - Convert Hub Forecast to WH Forecast")

# Step 1: Upload files
forecast_file = st.file_uploader("Upload Forecast File (Excel)", type=["xlsx", "xls"])
hub_map_file = st.file_uploader("Upload Hub-WH Mapping File (xlsx)", type="xlsx")
split_sku_file = st.file_uploader("Upload Split SKU List File (CSV)", type="csv")

if forecast_file and hub_map_file and split_sku_file:
    # Load the files
    forecast_df = pd.read_excel(forecast_file)
    hub_wh_map_df = pd.read_excel(hub_map_file)
    split_sku_df = pd.read_csv(split_sku_file)

    # Ensure column names match expected structure
    split_sku_df.columns = [col.lower() for col in split_sku_df.columns]
    if 'product_id' not in split_sku_df.columns:
        st.error("The split SKU list file must contain a 'product_id' column.")
    else:
        # Step 2: Mark SKUs to split
        st.write(split_sku_df.head())
        forecast_df['Split_SKU'] = forecast_df['Product ID'].isin(split_sku_df['product_id'])
        st.write("Forecast Hub ID dtype:", forecast_df['Hub ID'].dtype)
        st.write("Mapping Hub ID dtype:", hub_wh_map_df['Hub ID'].dtype)
        forecast_df['Hub ID'] = forecast_df['Hub ID'].astype(str).str.strip()
        hub_wh_map_df['Hub ID'] = hub_wh_map_df['Hub ID'].astype(str).str.strip()

        
        split_df = forecast_df[forecast_df['Split_SKU']].merge(
            hub_wh_map_df, on='Hub ID', how='left'
        )
        st.write("Columns in split_df:", split_df.columns.tolist())
        st.write(split_df.head())
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
        )['Forecast STEP 3'].sum()

        st.success("Forecast conversion successful!")
        st.dataframe(final_df)
        sku_count_df = final_df.groupby('WH ID')['Product ID'].nunique().reset_index()
        sku_count_df.columns = ['WH ID', 'Unique SKU Count']
        
        st.write("Unique SKU count per WH:")
        st.dataframe(sku_count_df)
        # Find split SKUs not in forecast
        missing_skus = split_sku_df[~split_sku_df['product_id'].isin(forecast_df['Product ID'].unique())]
        
        st.write("Split SKUs not found in forecast:")
        st.dataframe(missing_skus)

        # Step 1: Group by WH ID and Date, then sum the forecast
        summary_df = final_df.groupby(['WH ID', 'Date'], as_index=False)['Forecast STEP 3'].sum()
        
        # Step 2: Rename columns (optional)
        summary_df.columns = ['WH ID', 'Date', 'Total Forecast']
        
        # Step 3: Export to CSV
        summary_df.to_csv("summary_forecast_by_WHID.csv", index=False)
        
        # Step 4: Display in Streamlit
        st.write("Summary: Total Forecast by WH ID and Date")
        st.dataframe(summary_df)
        
        # Step 5: Provide download button (if in Streamlit)
        summ = summary_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Summary CSV", summ, "summary_forecast_by_WHID.csv", "text/csv")

        # Download output
        csv_output = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Forecast by WH (CSV)", csv_output, "ForecastSTEP3_by_WH.csv", "text/csv")

