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
        avg_kos, avg_stl = 100000, 40000  # Default hc
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
    change_date = pd.to_datetime("2025-03-10")

    # Generate OOS Projection
    start_date = pd.to_datetime("2025-02-28")
    target_dates = pd.date_range(start=start_date, periods=39, freq='D')

    oos_data = []

    last_7_days_oos = fixed_oos_data[fixed_oos_data["Date Key"] >= (pd.to_datetime("2025-03-04") - pd.Timedelta(days=2))]
    if not last_7_days_oos.empty:
        avg_oos_increase = last_7_days_oos["OOS%"].pct_change().mean()  # Compute average percentage change
    else:
        avg_oos_increase = 0  # 

    for date in target_dates:
        projected_oos = None  # Default to None
        supply = None  # Default supply

        if date in fixed_oos_data["Date Key"].values:
            projected_oos = fixed_oos_data.loc[fixed_oos_data["Date Key"] == date, "OOS%"].values[0]
            supply = supply_data.loc[supply_data["Date"] == date]
        elif date >= pd.to_datetime("2025-03-05") and date <= pd.to_datetime("2025-03-09"):
            supply = extended_supply.loc[extended_supply["Date"] == date]
            # Apply L7 trend to estimate OOS%
            prev_date = date - pd.Timedelta(days=1)
            prev_oos_values = [entry["Projected OOS%"] for entry in oos_data if entry["Date"] == prev_date.strftime("%d %b %Y")]
            if prev_oos_values:
                projected_oos = prev_oos_values[0] * (1 + avg_oos_increase)  # Apply trend
            else:
                projected_oos = last_7_days_oos["OOS%"].mean()  # Use L7 avg if no previous OOS
        elif date < change_date:
            supply = supply_data.loc[supply_data["Date"] == date]

        # Ensure supply is a valid DataFrame or Series
        if supply is not None and not supply.empty:
            supply = supply.squeeze()
        else:
            supply = pd.Series({"KOS": 100000, "STL": custom_stl_supply})

        total_supply = supply.get("KOS", 100000) + supply.get("STL", custom_stl_supply)
        daily_demand = demand_summary[demand_summary["Date Key"] == date]

        # If demand for the exact date does not exist, use the last available demand
        if daily_demand.empty:
            last_available_date = demand_summary[demand_summary["Date Key"] <= date]["Date Key"].max()
            daily_demand = demand_summary[demand_summary["Date Key"] == last_available_date]

        total_demand = daily_demand["Forecast"].sum() if not daily_demand.empty else 0
        normalized_demand = daily_demand["Normalized Demand"].values[0] if not daily_demand.empty else 0
        #st.write(f"{date.strftime('%d %b %Y')}: Demand -", daily_demand)


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
            supply_factor = max(0, min(1, (custom_stl_supply - 40000) / 35000 * 0.8))
            if days_after_change > 0 and days_after_change < 7:
                entry["Projected OOS%"] = round(projected_oos_8mar - (3 * days_after_change / 7) * ((supply_factor * 1.2) + 1), 2)
            elif days_after_change == 0 :
                entry["Projected OOS%"] = round(projected_oos_8mar - (2.5 / 7) * ((supply_factor * 1.2) + 1), 2)
            else:
                last_available_date = demand_summary[demand_summary["Date Key"] <= date]["Date Key"].max()
                last_available_demand = demand_summary[demand_summary["Date Key"] == last_available_date]["Forecast"].sum()
                forecast_value = last_available_demand if not pd.isna(last_available_demand) else demand_summary["Forecast"].mean()
                
                entry["Projected OOS%"] = round(forecast_value / 20000 * (1 - supply_factor), 2)


    df_oos_target = pd.DataFrame(oos_data)

    avg_inb_before = 161854
    avg_inb_now = 141532
    inbound_reduction_factor = avg_inb_before / avg_inb_now

    df_oos_target["OOS% w/o STOCK UP"] = df_oos_target["Projected OOS%"].astype(float) * inbound_reduction_factor
    #Based on D vs D-1 historical OOS records & L7 SO records-> rolling mean projections
    # Display Results
    st.markdown("### <span style='color:blue'>OOS% Projection with REAL HISTORICAL DATA</span>", unsafe_allow_html=True)
    st.markdown("""
    ### Notes:
    - **Next H+5 days (5-9 Mar)**: HC KOS 100K STL 40K, OOS fluctuates
    - **Set Changed Date (10 Mar)**: The starting date where we are optimistic to *ADHERE* to the specified SO numbers
    - **H+7 days from changed date**: Recovery period, slow decrease of OOS%
    - **H +>7 days**: OOS% starting to shift to normal, adapt to new SO qty following Demand Forecast
    """)
    st.markdown("### <span style='color:maroon'>TAMBAHAN IF WE DON'T STOCK UP</span>", unsafe_allow_html=True)
    assume = {
    "Category": [
        "Avg Sales", "Beginning Stock", "Exclude LDP (15%)", "Beginning Stock Final", 
        "Total Inbound Qty", "Daily Inbound Avg", "Inb STL Allocation", 
        "Inb KOS Allocation", "Ending Stock", "Ending DOI"
    ],
    "Current": [
        "120,000/day", "2,196,739", "(329,511)", "1,867,228", 
        "5,288,927", "251,854", "90,000", 
        "161,854", "1,811,155", "15.5 days"
    ],
    "Projection (No Stock Up)": [
        "120,000/day", "2,196,739", "(329,511)", "1,867,228", 
        "4,652,188", "221,532", "80,000", 
        "141,532", "1,560,000", "13 days"
    ]
    }
    
    # Create DataFrame
    assump = pd.DataFrame(assume)

    with st.expander("View Assumptions"):
        # Apply styling to left-align text and reduce font size
        st.dataframe(
            assump.style.set_properties(**{
                "text-align": "left",
                "font-size": "8px"
            }),
            use_container_width=True
        )
    #styled_table = assump.to_html(index=False, escape=False)
    
    def highlight_row(s):
        return ['background-color: yellow' if s["Date"] == "09 Mar 2025" else '' for _ in s]

    df_oos_target["KOS Supply"] = df_oos_target["KOS Supply"].apply(lambda x: f"{x:,.0f}")  # Format as thousands
    df_oos_target["STL Supply"] = df_oos_target["STL Supply"].apply(lambda x: f"{x:,.0f}")  # Format as thousands
    df_oos_target["Projected OOS%"] = df_oos_target["Projected OOS%"].apply(lambda x: f"{x:.2f}%")  # Format as percentage
    df_oos_target["OOS% w/o STOCK UP"] = df_oos_target["OOS% w/o STOCK UP"].apply(lambda x: f"{x:.2f}%")

    styled_df = df_oos_target.style.apply(highlight_row, axis=1)
    st.dataframe(styled_df, use_container_width=True)
    st.download_button("Download CSV", df_oos_target.to_csv(index=False), "oos_targetnew.csv", "text/csv")
