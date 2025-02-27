import streamlit as st
import pandas as pd
import numpy as np

# Load data
demand_forecast = pd.read_excel("forecast.xlsx")

# Define supply conditions
current_supply = {"KOS": 100000, "STL": 15000}  # 28 Feb-8 Mar
future_supply = {"KOS": 100000, "STL": 40000}  # 9 Mar onwards

# Define change date
change_date = pd.to_datetime("2025-03-09")

# Load SKUs available at STL
stl_skus = set(pd.read_csv("dedicated from stl 2.csv")["Product ID"])

# Base OOS rate
base_oos_rate = 13.85  # Fixed starting OOS percentage

# Forecast next 45 days
start_date = pd.to_datetime("2025-02-28")
target_dates = pd.date_range(start=start_date, periods=45, freq='D')
future_oos = []
for date in target_dates:
    supply = current_supply if date < change_date else future_supply
    temp_data = demand_forecast[demand_forecast["Date Key"] == date].copy()
    temp_data["Supply"] = temp_data["Product ID"].apply(lambda x: supply["STL"] if x in stl_skus else supply["KOS"])
    temp_data["Projected OOS%"] = base_oos_rate + np.maximum(0, (temp_data["Forecast"] - temp_data["Supply"]) / temp_data["Forecast"]) * 100
    future_oos.append({
        "Date": date.strftime("%d %b %Y"),
        "Outbound": supply["KOS"] + supply["STL"],
        "Projected OOS%": round(temp_data["Projected OOS%"].mean(), 2)
    })

# Display OOS projection
st.title("Out-of-Stock (OOS) Forecast")
df_oos = pd.DataFrame(future_oos)
st.dataframe(df_oos)

# Download button
#csv = df_oos.to_csv(index=False)
#st.download_button(label="Download Forecast CSV", data=csv, file_name="oos_forecast.csv", mime="text/csv")

