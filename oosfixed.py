import streamlit as st
import pandas as pd
import numpy as np


st.set_page_config(layout="wide")


# Streamlit UI
st.subheader("OOS Projection March - consider Unavailable stock KOS -> ga ke SO")


st.markdown("""
    <style>
    
    .css-1d391kg p {
        font-size: 6px;
    }
    .dataframe tbody tr th, .dataframe tbody tr td {
        font-size: 6px;
    }
    </style>
    """, unsafe_allow_html=True)


    
# Fixed supply values
KOS_SUPPLY = 100000
STL_SUPPLY = 80000


st.markdown("""
**Notes:**
- OOS Dry projection based on SO assumption of 100K and 80K daily from KOS and STL, with 90% FR for incoming PO coming next weeks. Thus, FR rate is safe.
- Some SKUs might have OOS WH in the coming days, based on Avg Sales and incoming PO Qty assumption -> translated into *'Qty ga ke SO'.*
- OOS Fresh is assumed based on the average contribution towards overall OOS trend, with fluctuations following the expected demand pattern.
""")
# File Upload for OOS WH
oos_wh_file = st.sidebar.file_uploader("Select OOS WH File", type=["xlsx"])

if oos_wh_file:
    # Load Data
    oos_wh_data = pd.read_excel(oos_wh_file)
    oos_wh_data["Date"] = pd.to_datetime(oos_wh_data["Date"])  # Convert OOS WH dates

    # OOS Projection
    target_dates = pd.date_range(start=pd.to_datetime("2025-03-13"), periods=26, freq='D')
    oos_data = []

    for date in target_dates:
        # Adjust KOS supply based on OOS WH data
        oos_wh_qty = oos_wh_data.loc[oos_wh_data["Date"] == date, "OOS Qty"].sum().astype(int)
        kos_supply = np.floor(max(0, KOS_SUPPLY - oos_wh_qty))

        # Calculate OOS percentage
        total_supply = kos_supply + STL_SUPPLY
        oos_percentage = (oos_wh_qty / total_supply) * 70 if total_supply > 0 else 0
        if oos_percentage > 0.02:
            oos_percentage *= 0.5
        # OOS Dry percentage data
        oos_percentage_data = {
            "12-Mar-25": 10.97, "13-Mar-25": 10.10, "14-Mar-25": 9.68, "15-Mar-25": 9.44,
            "16-Mar-25": 9.11, "17-Mar-25": 9.14, "18-Mar-25": 9.33, "19-Mar-25": 9.59,
            "20-Mar-25": 9.86, "21-Mar-25": 9.21, "22-Mar-25": 9.50, "23-Mar-25": 9.20,
            "24-Mar-25": 8.96, "25-Mar-25": 9.01, "26-Mar-25": 8.28, "27-Mar-25": 9.56,
            "28-Mar-25": 10.89, "29-Mar-25": 10.36, "30-Mar-25": 11.94, "31-Mar-25": 7.10,
            "01-Apr-25": 8.82, "02-Apr-25": 8.45, "03-Apr-25": 8.67, "04-Apr-25": 8.28,
            "05-Apr-25": 8.39, "06-Apr-25": 9.60, "07-Apr-25": 9.52,
        }

        # Projected OOS Dry percentage
        projected_oos = (oos_percentage_data.get(date.strftime("%d-%b-%y"), 0))#*0.95
        oos_dry_final = projected_oos + oos_percentage
        # Generate OOS Fresh percentage with similar fluctuation (scaled down to 1.2–2%)
        min_fresh = 1.2
        max_fresh = 2.0
        scaled_oos_fresh = min_fresh + (projected_oos / max(oos_percentage_data.values())) * (max_fresh - min_fresh)

        # Calculate final OOS percentage (Dry + Fresh + OOS Qty ga ke SO)
        oos_final = projected_oos + scaled_oos_fresh + oos_percentage

        oos_data.append({
            "Date": date.strftime("%d %b %Y"),
            "KOS SO": kos_supply,
            "STL SO": STL_SUPPLY,
            "Potential Qty gake SO WH OOS": oos_wh_qty,
            "add. OOS % impact": f"{oos_percentage:.2f}%",
            "Projected OOS Dry": f"{projected_oos:.2f}%",
            "Final OOS Dry": f"{oos_dry_final:.2f}%",
            "Assump. OOS Fresh": f"{scaled_oos_fresh:.2f}%",
            "OOS Final": f"{oos_final:.2f}%"
        })

    # Display the DataFrame
    def highlight_oos(row):
        color = 'background-color: #FFCCCC;' if float(row['Final OOS Dry'].replace('%', '')) > 0.10 else ''
        return [color] * len(row)

    df_oos_target = pd.DataFrame(oos_data)
    styled_df = df_oos_target.style.apply(highlight_oos, axis=1)
    st.dataframe(styled_df, use_container_width=True)
