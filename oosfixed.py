import streamlit as st
import pandas as pd
import numpy as np

# Streamlit UI
st.title("OOS 100K 80K - consider OOS WH")

# File Uploads
supply_file = st.sidebar.file_uploader("Upload Historical Supply SO (Exc. CANCELLED)", type=["xlsx"])
oos_file = st.sidebar.file_uploader("Upload Historical OOS% (Until Today)", type=["xlsx"])
oos_wh_file = st.sidebar.file_uploader("Upload OOS WH", type=["xlsx"])  # New input for OOS WH

# Fixed supply values
KOS_SUPPLY = 100000
STL_SUPPLY = 80000

if supply_file and oos_file:
    # Load Data
    supply_data = pd.read_excel(supply_file)
    fixed_oos_data = pd.read_excel(oos_file)
    demand_forecast = pd.read_excel("forecast dates.xlsx")
    oos_wh_data = pd.read_excel(oos_wh_file)
    
    supply_data["Date"] = pd.to_datetime(supply_data["Date"])
    fixed_oos_data["Date Key"] = pd.to_datetime(fixed_oos_data["Date Key"])
    demand_forecast["Date Key"] = pd.to_datetime(demand_forecast["Date Key"])
    oos_wh_data["Date"] = pd.to_datetime(oos_wh_data["Date"])  # Convert OOS WH dates


    # Sort supply data by date
    supply_data = supply_data.sort_values("Date")

    # Compute rolling mean for March 4-8
    forecasted_supply = []
    for target_date in pd.date_range("2025-03-12", "2025-03-31"):
        forecasted_supply.append({"Date": target_date, "KOS": KOS_SUPPLY, "STL": STL_SUPPLY})
    forecasted_supply = pd.DataFrame(forecasted_supply)
    extended_supply = pd.concat([supply_data, forecasted_supply]).drop_duplicates(subset=["Date"], keep="last")

    # Prepare Demand Data
    demand_summary = demand_forecast.groupby("Date Key")["Forecast"].sum().reset_index()
    max_demand = demand_summary["Forecast"].max()
    demand_summary["Normalized Demand"] = demand_summary["Forecast"] / max_demand

    # OOS Projection
  
    target_dates = pd.date_range(start=pd.to_datetime("2025-03-13"), periods=21, freq='D')
    oos_data = []

    for date in target_dates:
        supply = extended_supply.loc[extended_supply["Date"] == date]
        if supply.empty:
            supply = pd.Series({"KOS": 100000, "STL": 80000})
        else:
            supply = supply.squeeze()

        # Adjust KOS supply based on OOS WH data
        oos_wh_qty = oos_wh_data.loc[oos_wh_data["Date"] == date, "OOS Qty"].sum()
        supply["KOS"] = max(0, supply["KOS"] - oos_wh_qty)

        # Calculate OOS percentage
        total_supply = supply.get("KOS", 100000) + supply.get("STL", 80000)
        oos_percentage = (oos_wh_qty / total_supply) * 100 if total_supply > 0 else 0
        oos_percentage_data = {
        "12-Mar-25": 11.08,
        "13-Mar-25": 11.30,
        "14-Mar-25": 10.65,
        "15-Mar-25": 11.69,
        "16-Mar-25": 13.30,
        "17-Mar-25": 12.03,
        "18-Mar-25": 11.16,
        "19-Mar-25": 10.59,
        "20-Mar-25": 10.86,
        "21-Mar-25": 10.21,
        "22-Mar-25": 11.50,
        "23-Mar-25": 13.20,
        "24-Mar-25": 11.96,
        "25-Mar-25": 12.01,
        "26-Mar-25": 11.28,
        "27-Mar-25": 11.56,
        "28-Mar-25": 10.89,
        "29-Mar-25": 12.36,
        "30-Mar-25": 14.04,
        "31-Mar-25": 7.10,
        "01-Apr-25": 8.82,
        "02-Apr-25": 8.45,
        "03-Apr-25": 8.67,
        "04-Apr-25": 8.28,
        "05-Apr-25": 9.39,
        "06-Apr-25": 10.60,
        "07-Apr-25": 10.52,
        }
        projected_oos = oos_percentage_data.get(date.strftime("%d-%b-%y"), 0)

        oos_data.append({
            "Date": date.strftime("%d %b %Y"),
            "KOS Supply": supply.get("KOS", 100000),
            "STL Supply": supply.get("STL", 80000),
            "OOS Qty gake SO": oos_wh_qty,
            "OOS % tambah": f"{oos_percentage:.2f}%",
            "OOS Final": f"{projected_oos + oos_percentage:.2f}%"
        })
        
    df_oos_target = pd.DataFrame(oos_data)
    st.dataframe(df_oos_target, use_container_width=True)
