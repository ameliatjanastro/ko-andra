import streamlit as st
import pandas as pd
import numpy as np

# Streamlit UI
st.title("OOS Projection STL + SO Realistic")

# File Uploads
supply_file = st.sidebar.file_uploader("Upload Historical Supply SO (Exc. CANCELLED)", type=["xlsx"])
oos_file = st.sidebar.file_uploader("Upload Historical OOS% (Until Today)", type=["xlsx"])
inbound_file = st.sidebar.file_uploader("Upload Inbound Data", type=["csv"])
outbound_file = st.sidebar.file_uploader("Upload Outbound Data", type=["csv"])

# Custom Supply Inputs
custom_kos_supply = st.sidebar.number_input("KOS Supply After Mar 10", min_value=90000, value=100000, step=5000)
custom_stl_supply = st.sidebar.number_input("STL Supply After Mar 10", min_value=40000, value=40000, step=5000, max_value=100000)

if supply_file and oos_file and inbound_file and outbound_file:
    # Load Data
    supply_data = pd.read_excel(supply_file)
    fixed_oos_data = pd.read_excel(oos_file)
    inbound_data = pd.read_csv(inbound_file)
    outbound_data = pd.read_csv(outbound_file)
    demand_forecast = pd.read_excel("forecast dates.xlsx")  # Ensure this file exists
    
    # Convert Date Columns
    supply_data["Date"] = pd.to_datetime(supply_data["Date"])
    fixed_oos_data["Date Key"] = pd.to_datetime(fixed_oos_data["Date Key"])
    inbound_data["Date"] = pd.to_datetime(inbound_data["Date"])
    outbound_data["Date"] = pd.to_datetime(outbound_data["Date"])
    demand_forecast["Date Key"] = pd.to_datetime(demand_forecast["Date Key"])
    
    # Sort supply data
    supply_data = supply_data.sort_values("Date")
    supply_data[["KOS", "STL"]] = supply_data[["KOS", "STL"]].apply(pd.to_numeric, errors="coerce")

    # Define fixed supply days (unmodifiable)
    fixed_kos_zero_outbound_days = ["2025-04-18", "2025-04-19", "2025-04-20"]
    fixed_stl_zero_outbound_days = ["2025-04-25", "2025-04-26", "2025-04-27"]
    
    # Demand Summary
    demand_summary = demand_forecast.groupby("Date Key")["Forecast"].sum().reset_index()
    max_demand = demand_summary["Forecast"].max()
    demand_summary["Normalized Demand"] = demand_summary["Forecast"] / max_demand

    # Projection Start Date
    projection_start = pd.to_datetime("2025-03-25")

    # OOS Projection Adjustments
    oos_final_adjustments = []
    base_oos = 0.12  # Base OOS percentage
    daily_decrease = 0.003  # Daily decrease in OOS%
    supply_factor = max(0, min(1, (custom_stl_supply - 40000) / 25000 * 0.4))

    for date in pd.date_range("2025-03-25", "2025-04-30"):
        date_str = date.strftime("%Y-%m-%d")

        # If historical data exists, use it
        if date in fixed_oos_data["Date Key"].values:
            projected_oos = fixed_oos_data.loc[fixed_oos_data["Date Key"] == date, "OOS%"].values[0]
        else:
            # Fetch inbound and outbound data
            inbound_kos = inbound_data.loc[inbound_data["Date"] == date, "KOS"].sum()
            inbound_stl = inbound_data.loc[inbound_data["Date"] == date, "STL"].sum()
            outbound_kos = outbound_data.loc[outbound_data["Date"] == date, "KOS"].sum()
            outbound_stl = outbound_data.loc[outbound_data["Date"] == date, "STL"].sum()

            # Stock adjustments for specific dates
            if date_str in fixed_kos_zero_outbound_days:
                kos_stock = 0
                projected_oos = base_oos + 0.05  # Increase OOS due to 0 outbound
            elif date_str in fixed_stl_zero_outbound_days:
                stl_stock = 0
                projected_oos = base_oos + 0.08  # Higher OOS impact for STL 0 outbound
            else:
                kos_stock = custom_kos_supply if outbound_kos > 0 else 0
                stl_stock = custom_stl_supply if outbound_stl > 0 else 0
                oos_adjustment = -daily_decrease * (1 + supply_factor)
                stock_factor = max(0, min(1, ((kos_stock + stl_stock) - 100000) / 50000))  
                projected_oos = max(0, base_oos + oos_adjustment - (stock_factor * 0.04))

            # Adjustments for stock buildup (16 Apr +10K, 22 Apr +30K)
            if date_str == "2025-04-17":
                projected_oos *= 0.95  # Slight decrease in OOS
            elif date_str in ["2025-04-23", "2025-04-24"]:
                projected_oos *= 0.90  # Further decrease due to stock buildup

            # Demand factor influence
            daily_demand = demand_summary[demand_summary["Date Key"] == date]
            demand_factor = daily_demand["Normalized Demand"].values[0] if not daily_demand.empty else 1
            projected_oos *= demand_factor

        oos_final_adjustments.append({
            "Date": date.strftime("%d %b %Y"),
            "KOS Stock": f"{kos_stock:,.0f}" if 'kos_stock' in locals() else "N/A",
            "STL Stock": f"{stl_stock:,.0f}" if 'stl_stock' in locals() else "N/A",
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
