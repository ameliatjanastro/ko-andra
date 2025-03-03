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
    # Ensure the data is sorted before rolling calculation
    # Ensure the data is sorted
   # Ensure the data is sorted
    # Ensure data is sorted by Date
    supply_data = supply_data.sort_values("Date")
    
    # Convert supply columns to numeric
    supply_data[["KOS", "STL"]] = supply_data[["KOS", "STL"]].apply(pd.to_numeric, errors="coerce")
    
    # Initialize forecasted supply storage
    forecasted_supply = []
    
    # Create a copy of supply_data to update with forecasted values dynamically
    rolling_supply_data = supply_data.copy()
    
    # Compute rolling mean for March 4-8 using the last 3 available days (actual + forecasted)
    for target_date in pd.date_range("2025-03-04", "2025-03-08"):
        prev_days = rolling_supply_data[rolling_supply_data["Date"] < target_date].tail(3)  # Get last 3 available days
        
        if not prev_days.empty:
            avg_kos = prev_days["KOS"].mean()
            avg_stl = prev_days["STL"].mean()
        else:
            avg_kos, avg_stl = 100000, custom_stl_supply  # Default values if no data
        
        forecasted_supply.append({"Date": target_date, "KOS": avg_kos, "STL": avg_stl})
    
        # Append forecasted supply to rolling data for the next iterations
        rolling_supply_data = pd.concat([rolling_supply_data, pd.DataFrame(forecasted_supply[-1:], index=[0])])
    
    # Convert forecasted supply to DataFrame
    forecasted_supply = pd.DataFrame(forecasted_supply)
    
    # Merge forecasted supply with actual supply data
    extended_supply = pd.concat([supply_data, forecasted_supply]).drop_duplicates(subset=["Date"], keep="last")
    
    # Ensure proper sorting
    extended_supply = extended_supply.sort_values("Date")
    
    # Debugging: Display Rolling Supply Data
    st.write("Rolling Supply Data for March 4-8:")
    st.write(extended_supply[extended_supply["Date"].between("2025-03-04", "2025-03-08")])


    
    # Ensure proper sorting
    extended_supply = extended_supply.sort_values("Date")
    
    # Debugging: Display Rolling Supply Data
    st.write("Rolling Supply Data for March 4-8:")
    st.write(extended_supply[extended_supply["Date"].between("2025-03-04", "2025-03-08")])




    # Prepare Demand Data
    demand_summary = demand_forecast.groupby("Date Key")["Forecast"].sum().reset_index()
    max_demand = demand_summary["Forecast"].max()
    demand_summary["Normalized Demand"] = demand_summary["Forecast"] / max_demand

    # Set Custom STL Supply for Mar 9 Onwards
    custom_stl_supply = st.sidebar.number_input("STL Supply After Mar 9", min_value=40000, value=40000, step=5000, max_value=100000)
    change_date = pd.to_datetime("2025-03-09")

    # Generate OOS Projection
    start_date = pd.to_datetime("2025-02-28")
    target_dates = pd.date_range(start=start_date, periods=62, freq='D')

    oos_data = []

    for date in target_dates:
        projected_oos = None  # Default to None
        supply = None  # Default supply

        if date in fixed_oos_data["Date Key"].values:
            projected_oos = fixed_oos_data.loc[fixed_oos_data["Date Key"] == date, "OOS%"].values[0]
            supply = supply_data.loc[supply_data["Date"] == date]
        elif date >= pd.to_datetime("2025-03-04") and date <= pd.to_datetime("2025-03-08"):
            supply = extended_supply.loc[extended_supply["Date"] == date]
        elif date < change_date:
            supply = supply_data.loc[supply_data["Date"] == date]

        # Ensure supply is a valid DataFrame or Series
        if supply is not None and not supply.empty:
            supply = supply.squeeze()
        else:
            supply = pd.Series({"KOS": 100000, "STL": custom_stl_supply})

        total_supply = supply.get("KOS", 100000) + supply.get("STL", custom_stl_supply)
        daily_demand = demand_summary[demand_summary["Date Key"] == date]
        total_demand = daily_demand["Forecast"].sum() if not daily_demand.empty else 0
        normalized_demand = daily_demand["Normalized Demand"].values[0] if not daily_demand.empty else 0

        oos_data.append({
            "Date": date.strftime("%d %b %Y"),
            "KOS Supply": supply.get("KOS", 100000),
            "STL Supply": supply.get("STL", custom_stl_supply),
            "Projected OOS%": projected_oos if projected_oos is not None else np.nan,
        })

    # Get Projected OOS for March 8
    oos_values = [entry["Projected OOS%"] for entry in oos_data if pd.to_datetime(entry["Date"]) in pd.date_range("2025-03-04", "2025-03-07") and not pd.isna(entry["Projected OOS%"])]
    projected_oos_8mar = np.mean(oos_values) if oos_values else 12  # Default to 12 if no valid values

    # Adjust projection for March 9 onwards
    for entry in oos_data:
        date = pd.to_datetime(entry["Date"])
        if date >= change_date:
            days_after_change = (date - change_date).days
            supply_factor = max(0, min(1, (custom_stl_supply - 40000) / 35000 * 0.5))
            if days_after_change < 7:
                entry["Projected OOS%"] = round(projected_oos_8mar - (3 * days_after_change / 7) * ((supply_factor * 1.2) + 1), 2)
            else:
                entry["Projected OOS%"] = round(daily_demand["Forecast"].sum() / 22000 * (1 - supply_factor), 2)

    df_oos_target = pd.DataFrame(oos_data)

    # Display Results
    st.markdown("### <span style='color:blue'>OOS% Projection with Updated Supply Data</span>", unsafe_allow_html=True)
    st.dataframe(df_oos_target, use_container_width=True)
    st.download_button("Download CSV", df_oos_target.to_csv(index=False), "oos_targetnew.csv", "text/csv")
