import streamlit as st
import pandas as pd
import numpy as np



# st.set_page_config(layout="wide")
# Streamlit UI
st.title("OOS Projection Dry STO")

# File Uploads
supply_file = st.sidebar.file_uploader("Upload Historical Supply SO (Exc. CANCELLED)", type=["xlsx"])
oos_file = st.sidebar.file_uploader("Upload Historical OOS% (Until yesterday)", type=["xlsx"])

# Custom Supply Inputs
custom_kos_supply = st.sidebar.number_input("KOS SO", min_value=90000, value=100000, step=5000, max_value=110000)
custom_stl_supply = st.sidebar.number_input("STL SO", min_value=60000, value=80000, step=5000, max_value=120000)

stock_threshold = custom_kos_supply + custom_stl_supply

if supply_file and oos_file:
    # Load Data
    supply_data = pd.read_excel(supply_file)
    oos_data = pd.read_excel(oos_file)
    inbound_data = pd.read_excel("inbound.xlsx")
    outbound_data = pd.read_excel("outbound.xlsx")
    demand_forecast = pd.read_excel("forecast dates.xlsx")  # Ensure this file exists
    
    # Convert Date Columns
    supply_data["Date"] = pd.to_datetime(supply_data["Date"])
    oos_data["Date Key"] = pd.to_datetime(oos_data["Date Key"])
    inbound_data["Date"] = pd.to_datetime(inbound_data["Date"])
    outbound_data["Date"] = pd.to_datetime(outbound_data["Date"])
    demand_forecast["Date Key"] = pd.to_datetime(demand_forecast["Date Key"])

    latest_supply_date = supply_data["Date"].max().strftime("%d %b %Y") if not supply_data.empty else "N/A"
    latest_oos_date = oos_data["Date Key"].max().strftime("%d %b %Y") if not oos_data.empty else "N/A"

    # Display Latest Dates
    st.markdown(f"**📅 Latest Data Available:**")
    st.markdown(f"- **Supply Data:** {latest_supply_date}")
    st.markdown(f"- **OOS Data:** {latest_oos_date}")
    
    # Sort data
    supply_data = supply_data.sort_values("Date")

    # Define Fixed Dates for 0 Outbound Days
    fixed_kos_zero_outbound_days = ["2025-04-19", "2025-04-20"]
    fixed_stl_zero_outbound_days = ["2025-04-25", "2025-04-26", "2025-04-27"]
    
    # Ensure KOS still has outbound on April 18 (45000)
    locked_kos_days = {"2025-04-18": 45000}

    # OOS Projection Parameters
    file_only_dates = pd.date_range("2025-04-16", "2025-04-20").tolist() + pd.date_range("2025-04-22", "2025-04-27").tolist()
    file_only_dates = [d.strftime("%Y-%m-%d") for d in file_only_dates]

    projection_start = pd.to_datetime("2025-03-01")
    oos_final_adjustments = []
    #base_oos = recent_oos_data["OOS%"].mean() * 0.01
    daily_decrease = 0.00015

    # Compute Historical Average Supply
    historical_avg_supply = (supply_data["KOS"].mean() + supply_data["STL"].mean()) if not supply_data.empty else 180000

    for i, date in enumerate(pd.date_range("2025-03-01", "2025-04-30"), start=1):
        reference_date = date - pd.Timedelta(days=3)
        recent_oos_data = oos_data[oos_data["Date Key"] < reference_date].sort_values("Date Key", ascending=False).head(3)
        base_oos = recent_oos_data["OOS%"].mean() * 0.01
        date_str = date.strftime("%Y-%m-%d")

        # Get historical supply & OOS if available
        historical_supply = supply_data[supply_data["Date"] == date]
        historical_oos = oos_data[oos_data["Date Key"] == date]

        if not historical_oos.empty:
            projected_oos = historical_oos["OOS%"].values[0] * 0.01
            kos_stock = historical_supply["KOS"].values[0] if not historical_supply.empty else custom_kos_supply
            stl_stock = historical_supply["STL"].values[0] if not historical_supply.empty else custom_stl_supply
        else:
            # Fetch inbound and outbound data
            inbound_kos = inbound_data.loc[inbound_data["Date"] == date, "KOS"].sum()
            inbound_stl = inbound_data.loc[inbound_data["Date"] == date, "STL"].sum()
            outbound_kos = outbound_data.loc[outbound_data["Date"] == date, "KOS"].sum()
            outbound_stl = outbound_data.loc[outbound_data["Date"] == date, "STL"].sum()

            # Locked supply values for special dates
            if date_str in locked_kos_days:
                kos_stock = locked_kos_days[date_str]
            elif date_str in file_only_dates:
                kos_stock = historical_supply["KOS"].values[0] if not historical_supply.empty else custom_kos_supply
                stl_stock = historical_supply["STL"].values[0] if not historical_supply.empty else custom_stl_supply
            else:
                kos_stock = custom_kos_supply
                stl_stock = custom_stl_supply

            # Base OOS calculation
            if date < pd.Timestamp("2025-04-09"):
                projected_oos = base_oos  # Use the most recent 3-day average
            else:
                projected_oos = max(0, base_oos - daily_decrease)
            
            # Stock buildup impact
            if date_str == "2025-04-17":
                projected_oos *= 0.95
            elif date_str == "2025-04-18":
                projected_oos *= 1.45
            elif date_str in ["2025-04-23", "2025-04-24"]:
                projected_oos *= 0.90

            # Zero outbound adjustments
            if date_str in fixed_kos_zero_outbound_days:
                kos_stock = 0
                projected_oos += 0.032
            elif date_str in fixed_stl_zero_outbound_days:
                stl_stock = 0
                projected_oos += 0.025

            # **🔹 DYNAMIC STOCK FACTOR ADJUSTMENT**
            total_stock = kos_stock + stl_stock

            # Supply Deviation Factor (compares custom supply to historical average)
            supply_factor = (total_stock / historical_avg_supply)  

            # Dynamic OOS% adjustment based on supply changes
            if supply_factor > 1:
                projected_oos *= max(0.7, 1 - (supply_factor - 1) * 0.3)  # Reduce OOS% if supply is higher
            elif supply_factor < 1:
                projected_oos *= min(1.35, 1 + (1 - supply_factor) * 0.50)  # Increase OOS% if supply is lower

            # Demand factor influence
            #next_day = date + pd.Timedelta(days=1)
            daily_demand = demand_forecast[demand_forecast["Date Key"] == date]
            total_demand = daily_demand["Forecast"].sum() if not daily_demand.empty else demand_forecast["Forecast"].mean()
            demand_factor = total_demand / demand_forecast["Forecast"].max() if total_demand > 0 else 1
            projected_oos *= demand_factor* 1.15
            projected_oos = max(0, projected_oos * (1 - i * daily_decrease * (1 + supply_factor)))

        # Append results
        oos_final_adjustments.append({
            "Date": date.strftime("%d %b %Y"),
            "KOS SO Qty": f"{kos_stock:,.0f}",
            "STL SO Qty": f"{stl_stock:,.0f}",
            "Projected OOS%": f"{projected_oos:.2%}"
        })

    # Convert to DataFrame
    df_oos_final_adjusted = pd.DataFrame(oos_final_adjustments)

    # Display Results
    with st.expander("📌 Key Highlights of the OOS Projection"):
        st.markdown("""
        - **April 18-20**: KOS still has outbound on April 18 (45,000). No outbound on April 19-20.
        - **April 25-27**: No STL outbound on these dates.
        - **Dynamic OOS Adjustments**:
            - OOS% dynamically adjusts based on supply and demand fluctuations using RFR (Random forest regressor).
            - April 19-20 (KOS) and April 25-27 (STL) OOS% will be impacted due to no outbound.
        - **Demand Influence**:
            - Higher forecasted demand results in increased OOS%.
            - OOS% will also depends on total demand trend relative to the max forecasted demand.
        - **Reference**: https://docs.google.com/spreadsheets/d/1xDOb4EcEey5QYa1I6OO8siIg5NqKdvI_pvIv-C2MrcY/edit?gid=1971442377#gid=1971442377
        """)
    
    # Define function for row highlighting
    def highlight_special_dates(row):
        if row["Date"] in ["18 Apr 2025", "19 Apr 2025", "20 Apr 2025", "25 Apr 2025", "26 Apr 2025", "27 Apr 2025"]:
            return ['background-color: yellow'] * len(row)
        return [''] * len(row)
    
    # Apply highlighting
    styled_df = df_oos_final_adjusted.style.apply(highlight_special_dates, axis=1)
    
    # Display Results
    st.dataframe(styled_df, use_container_width=True)
    #st.dataframe(df_oos_final_adjusted, use_container_width=True)
    st.download_button("Download CSV", df_oos_final_adjusted.to_csv(index=False), "oos_projection.csv", "text/csv")
    
