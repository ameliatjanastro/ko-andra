import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Sales Scenario Histogram", layout="wide")

st.title("📊 SKU Sales Scenario Histogram (Pre-order Planning)")

# Upload file
uploaded_file = st.file_uploader("Upload your Excel or CSV file", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Preview
    st.subheader("📋 Data Preview")
    st.dataframe(df.head())

    # Rename columns if needed
    df = df.rename(columns=lambda x: x.strip())

    # Filter by L1 and product_type_name
    l1_options = df["L1"].dropna().unique()
    product_types = df["product_type_name"].dropna().unique()

    selected_l1 = st.multiselect("Filter by L1 Category", l1_options, default=list(l1_options))
    selected_type = st.multiselect("Filter by Product Type", product_types, default=list(product_types))

    filtered = df[
        df["L1"].isin(selected_l1) & df["product_type_name"].isin(selected_type)
    ]

    # Binning logic
    bin_edges = st.slider("Select Bin Edges", 0, 200, (0, 100), step=10)
    bins = np.arange(bin_edges[0], bin_edges[1] + 10, 10)

    st.subheader("📈 Histogram Comparison")

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.hist(filtered["Option Current - Aggressive"], bins=bins, alpha=0.6, label="Aggressive", color="orange")
    ax.hist(filtered["Option 1 - Moderate"], bins=bins, alpha=0.6, label="Moderate", color="blue")
    ax.hist(filtered["Option 2 - Conservatives"], bins=bins, alpha=0.6, label="Conservative", color="green")

    ax.set_xlabel("Avg Sales")
    ax.set_ylabel("SKU Count")
    ax.set_title("SKU Distribution by Sales Scenario")
    ax.legend()
    ax.grid(True)

    st.pyplot(fig)

else:
    st.info("Please upload your data file to begin.")
