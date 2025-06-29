import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Sales Scenario Histogram", layout="wide")
st.title("📊 SKU Sales Scenario Histogram (Pre-order Planning)")

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
    st.subheader("📋 Data Preview")
    st.dataframe(df.head())

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

    # Bin setup
    st.subheader("🎯 Configure Histogram Bins")
    bin_start = st.number_input("Bin Start", value=0)
    bin_end = st.number_input("Bin End", value=100)
    bin_step = st.number_input("Bin Step", value=10)
    bins = np.arange(bin_start, bin_end + bin_step, bin_step)

    st.subheader("📈 Histogram Comparison")
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.hist(df[col_aggressive], bins=bins, alpha=0.6, label="Aggressive", color="orange")
    ax.hist(df[col_moderate], bins=bins, alpha=0.6, label="Moderate", color="blue")
    ax.hist(df[col_conservative], bins=bins, alpha=0.6, label="Conservative", color="green")

    ax.set_xlabel("Average Sales")
    ax.set_ylabel("SKU Count")
    ax.set_title("SKU Distribution by Sales Scenario")
    ax.legend()
    ax.grid(True)

    st.pyplot(fig)

else:
    st.info("📥 Upload an Excel or CSV file with sales scenarios to begin.")

