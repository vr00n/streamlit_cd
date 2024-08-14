import streamlit as st
import pandas as pd
import requests
import time
from concurrent.futures import ThreadPoolExecutor  # Add this import

# Load the variables from the CSV file
variables_df = pd.read_csv('Variables.csv')

# Define your Census API key
API_KEY = 'fd901c69fb4729a262b7e163c1db69737513827d'

def fetch_data_in_batches(variables, api_key, batch_size=10, retries=3, timeout=10):
    # Break down variables into smaller batches
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
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    st.error("Failed to fetch data after multiple attempts.")
                    return None

    return full_df

def calculate_rankings(df, var_code):
    df['Rank'] = df[var_code].rank(ascending=False)
    return df

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

# Create tabs
tab1, tab2, tab3 = st.tabs(["Rank Congressional Districts", "Top N Districts by Measure", "Top 10 Measures for a District"])

with tab1:
    st.title('Census Data by Congressional District')
    st.write('This tab fetches and ranks census data for congressional districts across all states.')

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
            
            if st.button("Fetch and Rank Data"):
                # Fetch data for all states and all congressional districts
                df = fetch_data_in_batches([selected_var], API_KEY)
                
                if df is not None:
                    # Calculate rankings
                    ranked_df = calculate_rankings(df, selected_var)
                    
                    # Display the rankings with desired columns
                    ranked_df['State Name'] = ranked_df['NAME'].str.split(',').str[-1].str.strip()
                    st.write(f"Rankings for {selected_description} across all states")
                    st.dataframe(ranked_df[['congressional district', 'State Name', 'Rank', selected_var]])
        else:
            st.write("No variables found matching your search term.")
    else:
        st.write("Please enter a search term to find variable descriptions.")

with tab2:
    st.title('Top N Congressional Districts by Measure')
    st.write('This tab shows the top N congressional districts by a selected measure.')

    # Select a variable
    selected_description = st.selectbox("Select a measure", variables_df['Description'].values)
    
    # Find the corresponding variable code
    selected_var = variables_df[variables_df['Description'] == selected_description]['Variable'].values[0]

    # Select the number of top districts to show
    top_n = st.number_input("Select the number of top districts to display:", min_value=1, max_value=100, value=10)
    
    if st.button("Fetch Top N Districts"):
        # Fetch data for all states and all congressional districts
        df = fetch_data_in_batches([selected_var], API_KEY)
        
        if df is not None:
            # Calculate rankings
            ranked_df = calculate_rankings(df, selected_var)
            
            # Display only the top N rankings
            ranked_df['State Name'] = ranked_df['NAME'].str.split(',').str[-1].str.strip()
            st.write(f"Top {top_n} Congressional Districts by {selected_description}")
            st.dataframe(ranked_df[['congressional district', 'State Name', 'Rank', selected_var]].head(top_n))

with tab3:
    st.title('Top 10 Measures for a Congressional District')
    st.write('This tab shows all the measures where the selected congressional district ranks in the top 10.')

    # Fetch data for one of the measures to get the list of congressional districts
    sample_var = variables_df.iloc[0]['Variable']
    sample_df = fetch_data_in_batches([sample_var], API_KEY)
    if sample_df is not None:
        # Create a list of unique congressional districts
        sample_df['District Name'] = sample_df['NAME'].str.strip()
        congressional_districts = sample_df['District Name'].unique()
        
        # Select a congressional district from a selectbox
        district_name = st.selectbox("Select a congressional district", congressional_districts)

        if st.button("Fetch Top 10 Measures"):
            top_measures = []

            # Fetch data for all variables in smaller batches
            df = fetch_data_in_batches(variables_df['Variable'].values, API_KEY, batch_size=10)
            
            if df is not None:
                # Process each variable in parallel
                with ThreadPoolExecutor() as executor:
                    results = executor.map(lambda row: process_variable(row['Variable'], row['Description'], district_name, df), variables_df.iterrows())
                
                # Collect results
                top_measures = [result for result in results if result is not None]

                if top_measures:
                    top_measures_df = pd.DataFrame(top_measures)
                    st.write(f"Measures where {district_name} ranks in the top 10")
                    st.dataframe(top_measures_df)
                else:
                    st.write(f"No measures found where {district_name} is in the top 10.")
