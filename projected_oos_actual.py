import streamlit as st
import pandas as pd
import numpy as np

# Streamlit UI
st.title("OOS Projection STL + SO Realistic")

# File Uploads
supply_file = st.sidebar.file_uploader("Upload Historical Supply SO (Exc. CANCELLED)", type=["xlsx"])
oos_file = st.sidebar.file_uploader("Upload Historical OOS% (Until Today)", type=["xlsx"])

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
    for target_date in pd.date_range("2025-03-05", "2025-03-09"):
        #prev_days = rolling_supply_data[rolling_supply_data["Date"] < target_date].tail(7)  # Get last 3 available days
        avg_kos, avg_stl = 100000, 60000  # Default hc
        #if not prev_days.empty:
            #avg_kos = prev_days["KOS"].mean()
            #avg_stl = prev_days["STL"].mean()
        #else:
            #avg_kos, avg_stl = 100000, custom_stl_supply  # Default values if no data
        
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
    #st.write("Rolling Supply Data for March 4-8:")
    #st.write(extended_supply[extended_supply["Date"].between("2025-03-04", "2025-03-08")])
    
    # Prepare Demand Data
    demand_summary = demand_forecast.groupby("Date Key")["Forecast"].sum().reset_index()
    max_demand = demand_summary["Forecast"].max()
    demand_summary["Normalized Demand"] = demand_summary["Forecast"] / max_demand

    # Set Custom STL Supply for Mar 9 Onwards
    custom_stl_supply = st.sidebar.number_input("STL Supply After Mar 10", min_value=40000, value=40000, step=5000, max_value=100000)
    change_date = pd.Timestamp.today()
    
    # Generate OOS Projection
    start_date = pd.to_datetime("2025-02-28")
    target_dates = pd.date_range(start=start_date, periods=39, freq='D')
    
    oos_data = []
    
    # Use all available OOS data if projected OOS is 0%
    if fixed_oos_data["OOS%"].mean() == 0:
        avg_oos = fixed_oos_data["OOS%"].mean()
    else:
        last_3_days_oos = fixed_oos_data[fixed_oos_data["Date Key"] >= (pd.Timestamp.today() - pd.Timedelta(days=3))]
        avg_oos = last_3_days_oos["OOS%"].mean() if not last_3_days_oos.empty else fixed_oos_data["OOS%"].mean()
    
    daily_decrease = 0.003  # 0.3% decrease per day
    supply_factor = max(0, min(1, (custom_stl_supply - 40000) / 25000 * 0.4))
    
    for i, date in enumerate(target_dates):
        projected_oos = None
        supply = supply_data.loc[supply_data["Date"] == date]
        
        if date in fixed_oos_data["Date Key"].values:
            projected_oos = fixed_oos_data.loc[fixed_oos_data["Date Key"] == date, "OOS%"].values[0]
        elif date >= pd.Timestamp.today() + pd.Timedelta(days=1):
            daily_demand = demand_summary[demand_summary["Date Key"] == date]
            total_demand = daily_demand["Forecast"].sum() if not daily_demand.empty else demand_summary["Forecast"].mean()
            
            demand_mean = demand_summary["Forecast"].mean() if demand_summary["Forecast"].mean() > 0 else 1  # Prevent division by zero
            
            projected_oos = max(0, (avg_oos * (1 - i * daily_decrease * (1 - supply_factor))) * (total_demand / demand_mean))
        
        if supply.empty:
            supply = pd.Series({"KOS": 100000, "STL": custom_stl_supply})
        else:
            supply = supply.squeeze()
        
        oos_data.append({
            "Date": date.strftime("%d %b %Y"),
            "KOS Supply": supply.get("KOS", 100000),
            "STL Supply": supply.get("STL", custom_stl_supply),
            "Projected OOS%": float(projected_oos) if not np.isnan(projected_oos) else 0.0,
        })

        
    # Convert to DataFrame
    df_oos_target = pd.DataFrame(oos_data)
    
    # Display Results
    #st.markdown("### OOS% Projection with Demand Pattern")
    #st.dataframe(df_oos_target, use_container_width=True)
    #st.download_button("Download CSV", df_oos_target.to_csv(index=False), "oos_target.csv", "text/csv")


    with st.expander("View Assumptions"):
        # Apply styling to left-align text and reduce font size
        st.dataframe(
            df_oos_target.style.set_properties(**{
                "text-align": "left",
                "font-size": "8px"
            }),
            use_container_width=True
        )
    #styled_table = assump.to_html(index=False, escape=False)
    
    def highlight_row(s):
        return ['background-color: yellow' if s["Date"] == "10 Mar 2025" else '' for _ in s]

    df_oos_target["KOS Supply"] = df_oos_target["KOS Supply"].apply(lambda x: f"{x:,.0f}")  # Format as thousands
    df_oos_target["STL Supply"] = df_oos_target["STL Supply"].apply(lambda x: f"{x:,.0f}")  # Format as thousands
    df_oos_target["Projected OOS%"] = df_oos_target["Projected OOS%"].apply(lambda x: f"{x:.2f}%")  # Format as percentage

    styled_df = df_oos_target.style.apply(highlight_row, axis=1)
    st.dataframe(styled_df, use_container_width=True)
    st.download_button("Download CSV", df_oos_target.to_csv(index=False), "oos_targetnew.csv", "text/csv")
