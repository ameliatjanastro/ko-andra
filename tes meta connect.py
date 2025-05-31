import streamlit as st
import pandas as pd
import requests

# --- User inputs ---
st.title("Metabase Streamlit Connector")

metabase_url = "https://astro.metabaseapp.com"
username = st.text_input("Metabase Email", value="amelia.tjandra@astronauts.id")
password = st.text_input("Metabase Password", type="password")
question_id = 9968  # Your Metabase Question ID

if st.button("Fetch Data from Metabase"):
    with st.spinner("Authenticating with Metabase..."):
        # Step 1: Authenticate and get session token
        auth_res = requests.post(f"{metabase_url}/api/session", json={
            "username": username,
            "password": password
        })

        if auth_res.status_code == 200:
            token = auth_res.json()["id"]

            # Step 2: Query the question
            headers = {"X-Metabase-Session": token}
            query_url = f"{metabase_url}/api/card/{question_id}/query/json"
            query_res = requests.get(query_url, headers=headers)

            if query_res.status_code == 200:
                data = query_res.json()
                df = pd.DataFrame(data)
                st.success("Data fetched successfully!")
                st.dataframe(df)
            else:
                st.error(f"Failed to fetch data: {query_res.status_code}")
        else:
            st.error("Login failed! Please check your credentials.")
