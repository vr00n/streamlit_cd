import streamlit as st
import pandas as pd
import requests

# Load the variables from the CSV file
variables_df = pd.read_csv('Variables.csv')

# Define your Census API key
API_KEY = 'fd901c69fb4729a262b7e163c1db69737513827d'

def fetch_all_states_data(var_code, api_key, retries=3, timeout=10):
    url = f"https://api.census.gov/data/2017/acs/acs5/profile?get=NAME,{var_code}&for=congressional%20district:*&in=state:*&key={api_key}"
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data[1:], columns=data[0])
                df[var_code] = pd.to_numeric(df[var_code], errors='coerce')
                return df[['NAME', var_code, 'state', 'congressional district']]
            else:
                st.error(f"Failed to fetch data from the Census API: {response.status_code}")
                return None
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                st.warning(f"Request timed out. Retrying... ({attempt + 1}/{retries})")
                time.sleep(2)  # Wait before retrying
            else:
                st.error("Request timed out after multiple attempts.")
                return None
        except requests.exceptions.RequestException as e:
            st.error(f"An error occurred: {e}")
            return None
            
def calculate_rankings(df, var_code):
    df['Rank'] = df[var_code].rank(ascending=False)
    return df.sort_values(by='Rank')

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
                df = fetch_all_states_data(selected_var, API_KEY)
                
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
        df = fetch_all_states_data(selected_var, API_KEY)
        
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
    # For simplicity, we use the first variable in the CSV to fetch the list
    sample_var = variables_df.iloc[0]['Variable']
    sample_df = fetch_all_states_data(sample_var, API_KEY)
    if sample_df is not None:
        # Create a list of unique congressional districts
        sample_df['District Name'] = sample_df['NAME'].str.strip()
        congressional_districts = sample_df['District Name'].unique()
        
        # Select a congressional district from a selectbox
        district_name = st.selectbox("Select a congressional district", congressional_districts)

        if st.button("Fetch Top 10 Measures"):
            # Prepare a dataframe to store measures where the district is in the top 10
            top_measures = []

            # Iterate through all measures
            for _, row in variables_df.iterrows():
                selected_var = row['Variable']
                description = row['Description']
                
                # Fetch data for all states and all congressional districts
                df = fetch_all_states_data(selected_var, API_KEY)
                
                if df is not None:
                    # Calculate rankings
                    ranked_df = calculate_rankings(df, selected_var)
                    
                    # Check if the selected district is in the top 10
                if any(ranked_df['NAME'].str.contains(district_name, case=False, regex=False) & (ranked_df['Rank'] <= 10)):
                    top_measures.append({
                        'Measure': description,
                        'Variable': selected_var,
                        'Rank': ranked_df[ranked_df['NAME'].str.contains(district_name, case=False, regex=False)]['Rank'].values[0],
                        'Value': ranked_df[ranked_df['NAME'].str.contains(district_name, case=False, regex=False)][selected_var].values[0]
                    })
            
            if top_measures:
                top_measures_df = pd.DataFrame(top_measures)
                st.write(f"Measures where {district_name} ranks in the top 10")
                st.dataframe(top_measures_df)
            else:
                st.write(f"No measures found where {district_name} is in the top 10.")
