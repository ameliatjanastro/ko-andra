import streamlit as st
import pandas as pd
import numpy as np

st.title("OOS Forecast Model")

# Load data
demand_forecast = pd.read_excel("forecast.xlsx")
oos_data = pd.read_excel("raw.xlsx")
oos_data = oos_data[oos_data["Stock Hub"] == 0]
oos_rate_data = pd.read_excel("oos.xlsx")
oos_rate_data["Date Key"] = pd.to_datetime(oos_rate_data["Date Key"])

# Map OOS rate from separate dataset
oos_rate_by_date = dict(zip(oos_rate_data["Date Key"], oos_rate_data["OOS Rate"]))

# Define supply conditions
current_supply = {"KOS": 100000, "STL": 15000}  # 28 Feb-8 Mar
future_supply = {"KOS": 100000, "STL": 40000}  # 9 Mar onwards

# Define change date
change_date = "2025-03-09"

# Load SKUs available at STL
stl_skus = set(pd.read_csv("dedicated from stl 2.csv")["Product ID"])

# Forecast next 45 days
start_date = pd.to_datetime("2025-02-28")
target_dates = pd.date_range(start=start_date, periods=45, freq='D')
future_oos = []
for date in target_dates:
    supply = current_supply if date < pd.to_datetime(change_date) else future_supply
    temp_data = demand_forecast[demand_forecast["Date Key"] == date].copy()
    temp_data["OOS Rate"] = oos_rate_by_date.get(date, 0)
    future_oos.append({
        "Date": date.strftime("%d %b %Y"),
        "Outbound": supply["KOS"] + supply["STL"],
        "Projected OOS%": round(temp_data["OOS Rate"].mean(), 2)
    })

# Display OOS projection in Streamlit
df_oos = pd.DataFrame(future_oos)
st.dataframe(df_oos)
