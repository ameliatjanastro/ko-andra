import streamlit as st
import pandas as pd
import numpy as np

# Streamlit UI
st.title("OOS Projection STL + SO Realistic")

# File Uploads
supply_file = st.sidebar.file_uploader("Upload Historical Supply SO (Exc. CANCELLED)", type=["xlsx"])
oos_file = st.sidebar.file_uploader("Upload Historical OOS% (Until Today)", type=["xlsx"])

custom_kos_supply = st.sidebar.number_input("KOS Supply After Mar 10", min_value=90000, value=100000, step=5000)
custom_stl_supply = st.sidebar.number_input("STL Supply After Mar 10", min_value=40000, value=40000, step=5000, max_value=100000)

if supply_file and oos_file:
    # Load Data
    supply_data = pd.read_excel(supply_file)
    fixed_oos_data = pd.read_excel(oos_file)
    demand_forecast = pd.read_excel("forecast dates.xlsx")
    
    supply_data["Date"] = pd.to_datetime(supply_data["Date"])
    fixed_oos_data["Date Key"] = pd.to_datetime(fixed_oos_data["Date Key"])
    demand_forecast["Date Key"] = pd.to_datetime(demand_forecast["Date Key"])
    
    # Sort supply data
    supply_data = supply_data.sort_values("Date")
    supply_data[["KOS", "STL"]] = supply_data[["KOS", "STL"]].apply(pd.to_numeric, errors="coerce")
    
    # Define inbound and outbound schedules
    zero_inbound_kos_days = ["2025-04-18", "2025-04-19", "2025-04-20"]
    zero_inbound_stl_days = ["2025-04-18", "2025-04-20"]
    large_inbound_stl_day = "2025-04-19"
    
    zero_outbound_kos_days = ["2025-04-19", "2025-04-20"]
    partial_outbound_kos_day = "2025-04-18"
    full_outbound_kos_day = "2025-04-16"
    
    # Demand Summary
    demand_summary = demand_forecast.groupby("Date Key")["Forecast"].sum().reset_index()
    max_demand = demand_summary["Forecast"].max()
    demand_summary["Normalized Demand"] = demand_summary["Forecast"] / max_demand
    
    # OOS Projection Adjustments
    oos_final_adjustments = []
    base_oos = 0.12  # Base OOS percentage
    daily_decrease = 0.003  # Daily decrease in OOS%
    supply_factor = max(0, min(1, (custom_stl_supply - 40000) / 25000 * 0.4))
    
    for date in pd.date_range("2025-04-09", "2025-04-30"):
        date_str = date.strftime("%Y-%m-%d")
        
        if date_str in zero_outbound_kos_days:
            oos_adjustment = 0.07  # 7% increase on zero-outbound days for KOS
        elif date_str in zero_inbound_kos_days or date_str in zero_inbound_stl_days:
            oos_adjustment = 0.05  # 5% increase due to no inbound
        elif date_str == large_inbound_stl_day:
            oos_adjustment = -0.05  # 5% decrease due to large inbound
        elif date_str == partial_outbound_kos_day:
            oos_adjustment = 0.03  # 3% increase on partial outbound days
        elif date_str == full_outbound_kos_day:
            oos_adjustment = -0.02  # 2% decrease on full outbound days
        else:
            oos_adjustment = -daily_decrease * (1 + supply_factor)  # Normal daily decrease with supply factor
        
        # Get stock levels
        supply = supply_data[supply_data["Date"] == date]
        if supply.empty:
            kos_stock, stl_stock = custom_kos_supply, custom_stl_supply
        else:
            kos_stock = supply["KOS"].sum()
            stl_stock = supply["STL"].sum()
        
        # Normalize stock impact
        stock_factor = max(0, min(1, ((kos_stock + stl_stock) - 100000) / 50000))  
        
        # Adjust OOS%
        projected_oos = max(0, base_oos + oos_adjustment - (stock_factor * 0.04))
        
        # Apply demand trend factor
        daily_demand = demand_summary[demand_summary["Date Key"] == date]
        demand_factor = daily_demand["Normalized Demand"].values[0] if not daily_demand.empty else 1
        projected_oos *= demand_factor
        
        ooos_final_adjustments.append({
            "Date": date.strftime("%d %b %Y"),
            "KOS Supply": f"{kos_stock:,.0f}",
            "STL Supply": f"{stl_stock:,.0f}",
            "Projected OOS%": f"{projected_oos:.2%}"
        })
    
    # Convert to DataFrame
    df_oos_target = pd.DataFrame(oos_final_adjustments)
    
    # Display Results
    #st.dataframe(df_oos_final_adjusted, use_container_width=True)
    #st.download_button("Download CSV", df_oos_final_adjusted.to_csv(index=False), "oos_projection.csv", "text/csv")
    
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
