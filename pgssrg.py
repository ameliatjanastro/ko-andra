import pandas as pd

# Load input files
forecast_df = pd.read_csv("forecast.csv")  # Product ID, Date, Hub ID, ForecastSTEP 3
hub_wh_map_df = pd.read_csv("hub_wh_mapping.csv")  # Hub ID, WH ID
split_sku_df = pd.read_csv("split_sku_list.csv")  # Product ID column

# Step 1: Mark SKUs to split
forecast_df['Split_SKU'] = forecast_df['Product ID'].isin(split_sku_df['Product ID'])

# Step 2: Merge for split SKUs to get WH ID
split_df = forecast_df[forecast_df['Split_SKU']].merge(
    hub_wh_map_df, on='Hub ID', how='left'
)

# Step 3: Assign WH ID = 160 for non-split SKUs
nonsplit_df = forecast_df[~forecast_df['Split_SKU']].copy()
nonsplit_df['WH ID'] = 160

# Step 4: Combine both
combined_df = pd.concat([
    split_df[['Product ID', 'Date', 'WH ID', 'ForecastSTEP 3']],
    nonsplit_df[['Product ID', 'Date', 'WH ID', 'ForecastSTEP 3']]
])

# Step 5: Aggregate forecast in case multiple hubs map to the same WH
final_df = combined_df.groupby(['Product ID', 'Date', 'WH ID'], as_index=False)['ForecastSTEP 3'].sum()

# Optional: Rename output file
final_df.to_csv("ForecastSTEP3_by_WH.csv", index=False)
