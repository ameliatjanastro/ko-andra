import streamlit as st
import pandas as pd
import numpy as np

# Load data
demand_forecast = pd.read_excel("forecast dates.xlsx")
stl_skus = set(pd.read_csv("dedicated from stl 2.csv")["Product ID"])

# Define supply conditions
current_supply = {"KOS": 100000, "STL": 15000}  # 28 Feb-8 Mar
change_date = pd.to_datetime("2025-03-09")

# Base OOS rate
base_oos_rate = 13.85  # Fixed starting OOS percentage
expected_so = 140000  # Expected SO

demand_forecast["Date Key"] = pd.to_datetime(demand_forecast["Date Key"])
demand_summary = demand_forecast.groupby("Date Key")["Forecast"].sum().reset_index()

# Fixed OOS values from Feb 28 - Mar 9
fixed_oos = {
    pd.to_datetime("2025-02-28"): 13.37,
    pd.to_datetime("2025-03-01"): 13.43,
    pd.to_datetime("2025-03-02"): 13.44,
    pd.to_datetime("2025-03-03"): 13.51,
    pd.to_datetime("2025-03-04"): 13.66,
    pd.to_datetime("2025-03-05"): 13.71,
    pd.to_datetime("2025-03-06"): 13.73,
    pd.to_datetime("2025-03-07"): 13.83,
    pd.to_datetime("2025-03-08"): 13.85,
    pd.to_datetime("2025-03-09"): 12.63
}

# Streamlit UI
st.title("OOS Projection STL + SO :)")


custom_stl_supply = st.sidebar.number_input("STL Supply After Mar 9", min_value=40000, value=40000, step=5000,max_value=100000)
df_oos_target = []

#target_oos_percent = st.number_input("Target OOS Percentage", min_value=2.0, max_value=15.0, value=2.0, step=1.0) / 100
#df_oos_supply = []

start_date = pd.to_datetime("2025-02-28")
target_dates = pd.date_range(start=start_date, periods=62, freq='D')

max_demand = demand_summary["Forecast"].max()
demand_summary["Normalized Demand"] = demand_summary["Forecast"] / max_demand

for date in target_dates:
    if date < change_date:
        supply = current_supply.copy()
    else:
        supply = {"KOS": 100000, "STL": custom_stl_supply}
    
    total_supply = supply["KOS"] + supply["STL"]

    # Retrieve per-category demand
    daily_demand = demand_summary[demand_summary["Date Key"] == date]
    total_demand = daily_demand["Forecast"].sum() if not daily_demand.empty else 0
    kos_demand = total_demand * (2/3) *0.8
    stl_demand = total_demand * (1/3) *0.8

    # Use fixed OOS values or calculate dynamically
     # Use fixed OOS values or calculate dynamically following demand trend
    if date in fixed_oos:
        projected_oos = fixed_oos[date]
    else:
        days_after_change = (date - change_date).days
        if days_after_change < 7:
            supply_factor = max(0, min(1, (supply["STL"]-40000) / 35000 * 0.5))
            projected_oos = 12 - (3 * days_after_change / 7) *(1-supply_factor) # Gradual decrease to 9%
        else:
            normalized_demand = daily_demand["Normalized Demand"].values[0] if not daily_demand.empty else 0
            supply_factor = max(0, min(1, (supply["STL"]-40000) / 35000 * 0.5))
            projected_oos = daily_demand["Forecast"].sum()/22000 * (1-supply_factor)  # Fluctuates around 9%



     # Calculate final quantity needed for OOS = 0% and target OOS%
    #final_qty_oos_0 = expected_so + (projected_oos / 100) * expected_so * 1.1
    #final_qty_target_oos = expected_so + ((projected_oos / 100) - target_oos_percent) * expected_so * (1.275 + np.random.uniform(-0.05, 0.05))

    # Split final quantity into KOS and STL
    #final_qty_kos_oos_0 = final_qty_oos_0 * (2/3)
    #final_qty_stl_oos_0 = final_qty_oos_0 * (1/3) 
    #final_qty_kos_target_oos = final_qty_target_oos * (2/3) 
    #final_qty_stl_target_oos = final_qty_target_oos * (1/3)

    df_oos_target.append({
        "Date": date.strftime("%d %b %Y"),
        "KOS Supply": supply["KOS"],
        "STL Supply": supply["STL"],
        "Projected OOS%": round(projected_oos, 2),
    })
    
df_oos_target = pd.DataFrame(df_oos_target)


st.markdown("### <span style='color:blue'>OOS% Projection with STL SO Qty Changes</span>", unsafe_allow_html=True)
st.dataframe(df_oos_target.style.applymap(lambda x: 'background-color: lightgreen'), use_container_width=True)
