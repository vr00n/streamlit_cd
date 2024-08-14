import streamlit as st
import pandas as pd
import requests
from rapidfuzz import process

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

# User input for fuzzy search
search_term = st.text_input("Search for a variable description:")

if search_term:
    # Filter the dataframe based on the search term
    filtered_df = variables_df[variables_df['Description'].str.contains(search_term, case=False, na=False)]
    
    if not filtered_df.empty:
        # Let the user select from the filtered descriptions
        selected_description = st.selectbox("Select a variable description", filtered_df['Description'].values)
        
        # Find the corresponding variable code
        selected_var = filtered_df[filtered_df['Description'] == selected_description]['Variable'].values[0]
        
        # User selects the state code
        state_cd = st.selectbox("Select a state", sorted(variables_df['Category'].unique()))  # Example of dropdown
        
        if st.button("Fetch and Rank Data"):
            # Fetch data for all districts in the state
            df = fetch_all_districts_data(state_cd, selected_var, API_KEY)
            
            if df is not None:
                # Calculate rankings
                ranked_df = calculate_rankings(df, selected_var)
                
                # Display the rankings with desired columns
                ranked_df['State Name'] = state_cd
                st.write(f"Rankings for {selected_description} in State {state_cd}")
                st.dataframe(ranked_df[['congressional district', 'State Name', 'Rank', selected_var]])
    else:
        st.write("No variables found matching your search term.")
else:
    st.write("Please enter a search term to find variable descriptions.")
