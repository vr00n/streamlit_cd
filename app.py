import streamlit as st
import pandas as pd
import requests
import time
from concurrent.futures import ThreadPoolExecutor

# Load the variables from the CSV file
variables_df = pd.read_csv('Variables.csv')

# Define your Census API key
API_KEY = 'fd901c69fb4729a262b7e163c1db69737513827d'

# Function to fetch data in batches
def fetch_data_in_batches(variables, api_key, batch_size=10, retries=3, timeout=10):
    batched_variables = [variables[i:i + batch_size] for i in range(0, len(variables), batch_size)]
    full_df = pd.DataFrame()

    for batch in batched_variables:
        var_codes = ",".join(batch)
        url = f"https://api.census.gov/data/2017/acs/acs5/profile?get=NAME,{var_codes}&for=congressional%20district:*&in=state:*&key={api_key}"

        for attempt in range(retries):
            try:
                response = requests.get(url, timeout=timeout)
                if response.status_code == 200:
                    data = response.json()
                    df = pd.DataFrame(data[1:], columns=data[0])
                    for var in batch:
                        df[var] = pd.to_numeric(df[var], errors='coerce')
                    full_df = pd.concat([full_df, df], axis=1)
                    break
                else:
                    st.error(f"Failed to fetch data from the Census API: {response.status_code}")
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    st.warning(f"Request failed. Retrying... ({attempt + 1}/{retries})")
                    time.sleep(2 ** attempt)
                else:
                    st.error("Failed to fetch data after multiple attempts.")
                    return None

    return full_df

# Function to calculate rankings
def calculate_rankings(df, var_code):
    df['Rank'] = df[var_code].rank(ascending=False)
    return df

# Function to process and rank variables
def process_variable(var_code, description, district_name, df):
    ranked_df = calculate_rankings(df[['NAME', var_code, 'state', 'congressional district']].copy(), var_code)
    if any(ranked_df['NAME'].str.contains(district_name, case=False, regex=False) & (ranked_df['Rank'] <= 10)):
        return {
            'Measure': description,
            'Variable': var_code,
            'Rank': ranked_df[ranked_df['NAME'].str.contains(district_name, case=False, regex=False)]['Rank'].values[0],
            'Value': ranked_df[ranked_df['NAME'].str.contains(district_name, case=False, regex=False)][var_code].values[0]
        }
    return None

# Layout and UI
st.title("Compare Your Congressional District")
st.markdown("**Start by selecting your Congressional District**")

# Select Congressional District
district_name = st.selectbox("Select Congressional District", variables_df['Description'].unique())

# Create a 3-column layout
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    st.subheader("Select a Census Data Category")
    category = st.radio("Category", variables_df['Description'].unique())

with col2:
    st.subheader("Select a Measure to View Rankings")
    measures = variables_df[variables_df['Description'] == category]['Variable'].values
    measure = st.radio("Measure", measures)

with col3:
    st.subheader(f"Rankings for Congressional District: {district_name} in {category}")
    
    if st.button("Fetch and Compare"):
        df = fetch_data_in_batches([measure], API_KEY)
        if df is not None:
            ranked_df = calculate_rankings(df, measure)
            ranked_df['State Name'] = ranked_df['NAME'].str.split(',').str[-1].str.strip()
            st.dataframe(ranked_df[['congressional district', 'State Name', 'Rank', measure]])

# Additional functionality, filtering, and ranking logic can be added here.
