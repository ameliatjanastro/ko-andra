import streamlit as st
import pandas as pd
import numpy as np

# Streamlit UI
st.title("OOS Projection STL + SO Realistic")

# File Uploads
supply_file = st.sidebar.file_uploader("Upload Historical Supply SO (Exc. CANCELLED)", type=["xlsx"])
oos_file = st.sidebar.file_uploader("Upload Historical OOS% (Until Today)", type=["xlsx"])


# Custom Supply Inputs
custom_kos_supply = st.sidebar.number_input("KOS Supply After Mar 10", min_value=90000, value=100000, step=5000, max_value=110000)
custom_stl_supply = st.sidebar.number_input("STL Supply After Mar 10", min_value=80000, value=80000, step=5000, max_value=120000)

stock_threshold = custom_kos_supply + custom_stl_supply
stock_adjustment_range = stock_threshold * 0.5  # Instead of fixed 50,000

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

    # OOS Projection Parameters
    projection_start = pd.to_datetime("2025-03-01")
    oos_final_adjustments = []
    base_oos = oos_data["OOS%"].mean()*0.01
    daily_decrease = 0.002
    max_oos_increase = 0.02  # Limit OOS% increase to max 2%

    for i, date in enumerate(pd.date_range("2025-03-01", "2025-04-30"), start=1):
        date_str = date.strftime("%Y-%m-%d")

        # Get historical supply & OOS if available
        historical_supply = supply_data[supply_data["Date"] == date]
        historical_oos = oos_data[oos_data["Date Key"] == date]

        if not historical_oos.empty:
            # Use historical OOS data
            projected_oos = historical_oos["OOS%"].values[0]
            kos_stock = historical_supply["KOS"].values[0] if not historical_supply.empty else custom_kos_supply
            stl_stock = historical_supply["STL"].values[0] if not historical_supply.empty else custom_stl_supply
        else:
            # Fetch inbound and outbound data
            inbound_kos = inbound_data.loc[inbound_data["Date"] == date, "KOS"].sum()
            inbound_stl = inbound_data.loc[inbound_data["Date"] == date, "STL"].sum()
            outbound_kos = outbound_data.loc[outbound_data["Date"] == date, "KOS"].sum()
            outbound_stl = outbound_data.loc[outbound_data["Date"] == date, "STL"].sum()

            # ✅ LOCK KOS = 45,000 on April 18
            if date_str in locked_kos_days:
                kos_stock = locked_kos_days[date_str]
                
            
            # ✅ USE FILE DATA ONLY for 16-20 Apr & 22-27 Apr
            elif date_str in file_only_dates:
                kos_stock = historical_supply["KOS"].values[0] if not historical_supply.empty else custom_kos_supply
                stl_stock = historical_supply["STL"].values[0] if not historical_supply.empty else custom_stl_supply
            
            # ✅ CUSTOM SUPPLY for other dates
            else:
                kos_stock = custom_kos_supply
                stl_stock = custom_stl_supply

            # Base OOS calculation
            oos_adjustment = -daily_decrease
            projected_oos = max(0, base_oos + oos_adjustment)

            # Stock buildup impact (April 16 +10K, April 22 +30K)
            if date_str == "2025-04-17":
                projected_oos *= 0.95
            elif date_str == "2025-04-18":
                projected_oos *= 1.25
            elif date_str in ["2025-04-23", "2025-04-24"]:
                projected_oos *= 0.90

            # 0 outbound adjustments
            if date_str in fixed_kos_zero_outbound_days:
                kos_stock = 0
                projected_oos += 0.045  # Reduced impact (was +0.05)
            elif date_str in fixed_stl_zero_outbound_days:
                stl_stock = 0
                projected_oos += 0.05  # Reduced impact (was +0.08)

            # **🔹 DYNAMIC STOCK FACTOR ADJUSTMENT**
            total_stock = kos_stock + stl_stock

            # ✅ Now based on **custom stock values**, not fixed numbers
            stock_factor = max(0, min(1, (total_stock - 40000) / 25000))
            

            # ✅ STRONGER IMPACT: OOS% now reduces up to **3%** based on supply
            projected_oos = max(0, projected_oos - (stock_factor * 0.003))

            # Demand factor influence
            daily_demand = demand_forecast[demand_forecast["Date Key"] == date]
            demand_summary = demand_forecast.groupby("Date Key")["Forecast"].sum().reset_index()
            total_demand = daily_demand["Forecast"].sum() if not daily_demand.empty else demand_summary["Forecast"].mean()
            demand_mean = demand_summary["Forecast"].mean() if demand_summary["Forecast"].mean() > 0 else 1  # Prevent division by zero
            demand_factor = daily_demand["Forecast"].values[0] / demand_forecast["Forecast"].max() if not daily_demand.empty else 1
            projected_oos *= demand_factor
            projected_oos = max(0, (projected_oos * (1 - i * daily_decrease * (1 + stock_factor))) * (total_demand / demand_mean)*1.05)

        # Append results
        oos_final_adjustments.append({
            "Date": date.strftime("%d %b %Y"),
            "KOS Stock": f"{kos_stock:,.0f}",
            "STL Stock": f"{stl_stock:,.0f}",
            "Projected OOS%": f"{projected_oos:.2%}"
        })
    
    # Convert to DataFrame
    df_oos_final_adjusted = pd.DataFrame(oos_final_adjustments)
    
    # Display Results
    st.dataframe(df_oos_final_adjusted, use_container_width=True)
    st.download_button("Download CSV", df_oos_final_adjusted.to_csv(index=False), "oos_projection.csv", "text/csv")
    
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

    #df_oos_target["KOS Supply"] = df_oos_target["KOS Supply"].apply(lambda x: f"{x:,.0f}")  # Format as thousands
    #df_oos_target["STL Supply"] = df_oos_target["STL Supply"].apply(lambda x: f"{x:,.0f}")  # Format as thousands
    #df_oos_target["Projected OOS%"] = df_oos_target["Projected OOS%"].apply(lambda x: f"{x:.2f}%")  # Format as percentage

    #styled_df = df_oos_target.style.apply(highlight_row, axis=1)
    #st.dataframe(styled_df, use_container_width=True)
    #st.download_button("Download CSV", df_oos_target.to_csv(index=False), "oos_targetnew.csv", "text/csv")
