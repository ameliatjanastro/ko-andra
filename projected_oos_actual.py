import streamlit as st
import pandas as pd
import numpy as np

# Streamlit UI
st.title("OOS Projection STL + SO New")

# File Uploads
supply_file = st.sidebar.file_uploader("Upload Supply CSV", type=["xlsx"])
oos_file = st.sidebar.file_uploader("Upload Fixed OOS CSV (Until Mar 3)", type=["xlsx"])

if supply_file and oos_file:
    # Load Data
    supply_data = pd.read_excel(supply_file)
    fixed_oos_data = pd.read_excel(oos_file)
    demand_forecast = pd.read_excel("forecast dates.xlsx")
    
    supply_data["Date"] = pd.to_datetime(supply_data["Date"])
    fixed_oos_data["Date Key"] = pd.to_datetime(fixed_oos_data["Date Key"])
    demand_forecast["Date Key"] = pd.to_datetime(demand_forecast["Date Key"])
    
    # Compute Rolling Supply for Mar 4-8
    avg_supply = supply_data.set_index("Date").rolling(3).mean().reset_index()
    avg_supply = avg_supply[supply_data["Date"] >= "2025-03-04"]
    
    # Prepare Demand Data
    demand_summary = demand_forecast.groupby("Date Key")["Forecast"].sum().reset_index()
    max_demand = demand_summary["Forecast"].max()
    demand_summary["Normalized Demand"] = demand_summary["Forecast"] / max_demand
    
    # Set Custom STL Supply for Mar 9 Onwards
    custom_stl_supply = st.sidebar.number_input("STL Supply After Mar 9", min_value=40000, value=40000, step=5000, max_value=100000)
    change_date = pd.to_datetime("2025-03-09")
    
    # Generate OOS Projection
    df_oos_target = []
    start_date = pd.to_datetime("2025-02-28")
    target_dates = pd.date_range(start=start_date, periods=62, freq='D')
    
    for date in target_dates:
        projected_oos = None  # Default to None to check if it remains unset

        if date in fixed_oos_data["Date Key"].values:
            projected_oos = fixed_oos_data.loc[fixed_oos_data["Date Key"] == date, "OOS%"].values[0]
        elif "2025-03-04" <= str(date) <= "2025-03-08":
            supply = avg_supply.loc[avg_supply["Date"] == date]
            if not supply.empty:
                supply = supply.iloc[0]
            else:
                supply = pd.Series({"KOS": 100000, "STL": custom_stl_supply})
            
        #projected_oos = None  # Default if not found
    
        # Get OOS if available
        #if date in fixed_oos_data["Date Key"].values:
            #projected_oos = fixed_oos_data.loc[fixed_oos_data["Date Key"] == date, "OOS%"].values[0]
        
        # Determine supply source
        #if pd.to_datetime("2025-03-04") <= date <= pd.to_datetime("2025-03-08"):
            #supply = avg_supply[avg_supply["Date"] == date]
        #elif date < change_date:
            #supply = supply_data[supply_data["Date"] == date]
        #else:
            #supply = pd.DataFrame([{"KOS": 100000, "STL": custom_stl_supply}])  # Use DataFrame for consistency
    
        # Ensure supply is valid
        #if not supply.empty:
            #supply = supply.iloc[0]  # Use first row
        #else:
            #supply = {"KOS": 100000, "STL": custom_stl_supply}  # Fallback values

        
        total_supply = supply.get("KOS", 100000) + supply.get("STL", custom_stl_supply)
        daily_demand = demand_summary[demand_summary["Date Key"] == date]
        total_demand = daily_demand["Forecast"].sum() if not daily_demand.empty else 0
        normalized_demand = daily_demand["Normalized Demand"].values[0] if not daily_demand.empty else 0
        projected_oos = (total_demand / total_supply) * 100 if total_supply > 0 else 100  # Estimate OOS%
            
        df_oos_target.append({
            "Date": date.strftime("%d %b %Y"),
            "KOS Supply": supply["KOS"] if isinstance(supply, pd.Series) else 100000,
            "STL Supply": supply["STL"] if isinstance(supply, pd.Series) else custom_stl_supply,
            "Projected OOS%": projected_oos,
        })
        
    valid_oos_values = [entry["Projected OOS%"] for entry in df_oos_target 
                    if pd.to_datetime(entry["Date"]) in pd.date_range("2025-03-04", "2025-03-07") 
                    and entry["Projected OOS%"] is not None]

    projected_oos_8mar = np.mean(valid_oos_values) if valid_oos_values else 0  # Fallback to 0 if empty
        
    # Adjust projection for March 9 onwards
    for entry in df_oos_target:
        date = pd.to_datetime(entry["Date"])
        if date >= change_date:
            days_after_change = (date - change_date).days
            supply_factor = max(0, min(1, (custom_stl_supply - 40000) / 35000 * 0.5))
            if days_after_change < 7:
                entry["Projected OOS%"] = round(projected_oos_8mar - (3 * days_after_change / 7) * ((supply_factor * 1.2) + 1), 2)
            else:
                entry["Projected OOS%"] = round(daily_demand["Forecast"].sum() / 22000 * (1 - supply_factor), 2)
        
    df_oos_target = pd.DataFrame(df_oos_target)

    # Display Results
    st.markdown("### <span style='color:blue'>OOS% Projection with Updated Supply Data</span>", unsafe_allow_html=True)
    st.dataframe(df_oos_target, use_container_width=True)
    st.download_button("Download CSV", df_oos_target.to_csv(index=False), "oos_target_new.csv", "text/csv")
