import streamlit as st
import pandas as pd
import requests

# Load the variables from the CSV file
variables_df = pd.read_csv('Variables.csv')

# Define your Census API key
API_KEY = 'fd901c69fb4729a262b7e163c1db69737513827d'

def fetch_all_districts_data(state_code, var_code, api_key):
    url = f"https://api.census.gov/data/2017/acs/acs5/profile?get=NAME,{var_code}&for=congressional%20district:*&in=state:{state_code}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data[1:], columns=data[0])
        df[var_code] = pd.to_numeric(df[var_code], errors='coerce')
        return df[['NAME', var_code, 'state', 'congressional district']]
    else:
        st.error("Failed to fetch data from the Census API")
        return None

def calculate_rankings(df, var_code):
    df['Rank'] = df[var_code].rank(ascending=False)
    return df.sort_values(by='Rank')

st.title('Census Data by Congressional District')
st.write('This app fetches and ranks census data for congressional districts.')

# User input for state code
state_cd = st.text_input("Enter state code (e.g., 36 for NY):", "36")

# Select a variable from the loaded CSV
selected_var = st.selectbox("Select a variable", variables_df['Variable Code'].values)

if st.button("Fetch and Rank Data"):
    # Fetch data for all districts in the state
    df = fetch_all_districts_data(state_cd, selected_var, API_KEY)
    
    if df is not None:
        # Calculate rankings
        ranked_df = calculate_rankings(df, selected_var)
        
        # Display the rankings
        var_name = variables_df[variables_df['Variable Code'] == selected_var]['Variable Name'].values[0]
        st.write(f"Rankings for {var_name} in State {state_cd}")
        st.dataframe(ranked_df)

# Display the available variables
st.write("Available Variables:")
st.dataframe(variables_df.head())
