import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="POIA Avg Sales Histogram")

st.markdown(
    """
    <style>
        body {
            zoom: 90%;
        }
    </style>
    """,
    unsafe_allow_html=True
)
st.title("📊 POIA Avg Sales Histogram")

uploaded_file = st.file_uploader("Upload your Excel or CSV file", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Clean column names
    df.columns = df.columns.str.strip()

    # ✅ Define these early
    col_aggressive = "Option Current - Aggressive"
    col_moderate = "Option 1 - Moderate"
    col_conservative = "Option 2 - Conservatives"

    # Preview
    #st.subheader("📋 Data Preview")
    #st.dataframe(df.head())

    # Optional filters
    if "L1" in df.columns and "product_type_name" in df.columns:
        l1_options = df["L1"].dropna().unique()
        product_types = df["product_type_name"].dropna().unique()

        selected_l1 = st.multiselect("Filter by L1 Category", l1_options, default=list(l1_options))
        selected_type = st.multiselect("Filter by Product Type", product_types, default=list(product_types))

        df = df[
            df["L1"].isin(selected_l1) & df["product_type_name"].isin(selected_type)
        ]

    # ✅ Clean data
    df[col_aggressive] = pd.to_numeric(df[col_aggressive], errors="coerce")
    df[col_moderate] = pd.to_numeric(df[col_moderate], errors="coerce")
    df[col_conservative] = pd.to_numeric(df[col_conservative], errors="coerce")
    df = df.dropna(subset=[col_aggressive, col_moderate, col_conservative], how='all')

    st.subheader("🎯 Configure Histogram Bins")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        bin_start = st.number_input("Bin Start", value=0, step =10 )
    with col2:
        bin_end = st.number_input("Bin End", value=100, step =10 )
    with col3:
        bin_step = st.number_input("Bin Step", value=10, step =10 )
    
    bins = np.arange(bin_start, bin_end + bin_step, bin_step)

    chart_type = st.radio(
    "Choose chart style:",
    ["Overlayed Histogram", "Grouped Bar Chart"],
    index=0,
    horizontal=True
    )

    st.subheader("📈 Histogram Comparison")
    fig, ax = plt.subplots(figsize=(12, 5))

    if chart_type == "Overlayed Histogram":
        # Transparent histograms
        ax.hist(df[col_aggressive], bins=bins, alpha=0.6, label="Aggressive", color="red")
        ax.hist(df[col_moderate], bins=bins, alpha=0.6, label="Moderate", color="yellow")
        ax.hist(df[col_conservative], bins=bins, alpha=0.6, label="Conservative", color="blue")
    else:
        # Calculate histogram frequencies
        aggr_hist, _ = np.histogram(df[col_aggressive], bins=bins)
        mod_hist, _ = np.histogram(df[col_moderate], bins=bins)
        cons_hist, _ = np.histogram(df[col_conservative], bins=bins)
    
        bin_centers = (bins[:-1] + bins[1:]) / 2
        width = (bins[1] - bins[0]) / 4
    
        ax.bar(bin_centers - width, aggr_hist, width=width, label="Aggressive", color="red")
        ax.bar(bin_centers,         mod_hist, width=width, label="Moderate", color="yellow")
        ax.bar(bin_centers + width, cons_hist, width=width, label="Conservative", color="blue")
    
    # Common chart formatting
    ax.set_xlabel("Average Sales")
    ax.set_ylabel("SKU Count")
    ax.set_title("SKU Distribution by Sales Scenario")
    ax.legend()
    ax.grid(True)
    
    st.pyplot(fig)

else:
    st.info("📥 Upload an Excel or CSV file with sales scenarios to begin.")

