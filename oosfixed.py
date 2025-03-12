import streamlit as st
import pandas as pd
import numpy as np

# Streamlit UI
st.title("OOS 100K 80K - consider Avail stock KOS -> ga ke SO")


st.markdown("""
    <style>
    .css-1d391kg p {
        font-size: 12px;
    }
    .dataframe tbody tr th, .dataframe tbody tr td {
        font-size: 10px;
    }
    .css-12oz5g7 {
        zoom: 0.9;
    }
    </style>
    """, unsafe_allow_html=True)


# File Upload for OOS WH
oos_wh_file = st.sidebar.file_uploader("Upload OOS WH", type=["xlsx"])  # New input for OOS WH

# Fixed supply values
KOS_SUPPLY = 100000
STL_SUPPLY = 80000

if oos_wh_file:
    # Load Data
    oos_wh_data = pd.read_excel(oos_wh_file)
    oos_wh_data["Date"] = pd.to_datetime(oos_wh_data["Date"])  # Convert OOS WH dates

    # OOS Projection
    target_dates = pd.date_range(start=pd.to_datetime("2025-03-13"), periods=21, freq='D')
    oos_data = []

    for date in target_dates:
        # Adjust KOS supply based on OOS WH data
        oos_wh_qty = oos_wh_data.loc[oos_wh_data["Date"] == date, "OOS Qty"].sum().astype(int)
        kos_supply = np.floor(max(0, KOS_SUPPLY - oos_wh_qty))

        # Calculate OOS percentage
        total_supply = kos_supply + STL_SUPPLY
        oos_percentage = (oos_wh_qty / total_supply) * 100 if total_supply > 0 else 0

        # OOS Dry percentage data
        oos_percentage_data = {
            "12-Mar-25": 11.08, "13-Mar-25": 11.30, "14-Mar-25": 10.65, "15-Mar-25": 11.69,
            "16-Mar-25": 13.30, "17-Mar-25": 12.03, "18-Mar-25": 11.16, "19-Mar-25": 10.59,
            "20-Mar-25": 10.86, "21-Mar-25": 10.21, "22-Mar-25": 11.50, "23-Mar-25": 13.20,
            "24-Mar-25": 11.96, "25-Mar-25": 12.01, "26-Mar-25": 11.28, "27-Mar-25": 11.56,
            "28-Mar-25": 10.89, "29-Mar-25": 12.36, "30-Mar-25": 14.04, "31-Mar-25": 7.10,
            "01-Apr-25": 8.82, "02-Apr-25": 8.45, "03-Apr-25": 8.67, "04-Apr-25": 8.28,
            "05-Apr-25": 9.39, "06-Apr-25": 10.60, "07-Apr-25": 10.52,
        }

        # Projected OOS Dry percentage
        projected_oos = oos_percentage_data.get(date.strftime("%d-%b-%y"), 0)

        # Generate OOS Fresh percentage with similar fluctuation (scaled down to 1.2–2%)
        min_fresh = 1.2
        max_fresh = 2.0
        scaled_oos_fresh = min_fresh + (projected_oos / max(oos_percentage_data.values())) * (max_fresh - min_fresh)

        # Calculate final OOS percentage (Dry + Fresh + OOS Qty ga ke SO)
        oos_final = projected_oos + scaled_oos_fresh + oos_percentage

        oos_data.append({
            "Date": date.strftime("%d %b %Y"),
            "KOS Supply": kos_supply,
            "STL Supply": STL_SUPPLY,
            "Projected OOS Dry": f"{projected_oos:.2f}%",
            "Potential Qty gake SO WH OOS": oos_wh_qty,
            "OOS % tambah": f"{oos_percentage:.2f}%",
            "OOS Fresh": f"{scaled_oos_fresh:.2f}%",
            "OOS Final": f"{oos_final:.2f}%"
        })

    # Display the DataFrame
    df_oos_target = pd.DataFrame(oos_data)
    st.dataframe(df_oos_target, use_container_width=True)
