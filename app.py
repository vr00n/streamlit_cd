import streamlit as st
import pandas as pd
import requests
import time
from concurrent.futures import ThreadPoolExecutor

# Load the variables from the CSV file
variables_df = pd.read_csv('Variables.csv')

# Filter variables that end with "PE"
variables_df = variables_df[variables_df['Variable'].str.endswith("PE")]

# Check if the DataFrame is empty after filtering
if variables_df.empty:
    st.error("No variables found ending with 'PE'. Please check the CSV file.")
else:
    # Split the descriptions into Category and Measure
    def extract_category_and_measure(description):
        parts = description.split('!!')
        if len(parts) > 2:
            category = parts[1]
            measure = ': '.join(parts[2:])
        else:
            category = 'Unknown'
            measure = description  # Use the whole description if it doesn't fit the expected format
        return category, measure

    variables_df[['Category', 'Measure']] = variables_df['Description'].apply(lambda x: pd.Series(extract_category_and_measure(x)))

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
    def calculate_rankings(df, var_code, rank_within_state=False, state=None):
        if rank_within_state and state is not None:
            df = df[df['state'] == state]
    
        # Ensure we are ranking based on the correct variable column
        if var_code in df.columns:
            df['Rank'] = df[var_code].rank(ascending=False)
        else:
            st.error(f"Variable column '{var_code}' not found in the dataset.")
    
    return df

        if rank_within_state and state is not None:
            df = df[df['state'] == state]
        df['Rank'] = df[var_code].rank(ascending=False)
        return df

    # Fetch data for a sample variable to get Congressional District names
    sample_var = variables_df.iloc[0]['Variable']
    sample_df = fetch_data_in_batches([sample_var], API_KEY)

    if sample_df is not None:
        # Extract Congressional District names
        sample_df['District Name'] = sample_df['NAME'].str.strip()
        congressional_districts = sample_df['District Name'].unique()

        # Layout and UI
        st.title("Compare Your Congressional District")
        st.markdown("**Start by selecting your Congressional District**")

        # Dropdown for Congressional Districts
        district_name = st.selectbox("Select Congressional District", congressional_districts)

        # Create a wider layout
        col1, col2, col3 = st.columns([2, 2, 3])

        with col1:
            st.subheader("Select a Census Data Category")
            category = st.radio("Category", variables_df['Category'].unique())

        with col2:
            st.subheader("Select a Measure to View Rankings")
            measures = variables_df[variables_df['Category'] == category]['Measure'].unique()
            measure = st.radio("Measure", measures)

        with col3:
            st.subheader(f"Rankings for Congressional District: {district_name} in {category}")

            # Option to rank within state or nationally
            ranking_scope = st.radio("Rank within:", ['State', 'Nation'])

            if st.button("Fetch and Compare"):
                # Determine if ranking is within state or nationally
                rank_within_state = (ranking_scope == 'State')

                # Extract state code from district name (assuming the state is at the end of the district name)
                selected_state = district_name.split(',')[-1].strip()

                # Find the variable code for the selected measure
                selected_var = variables_df[(variables_df['Category'] == category) & (variables_df['Measure'] == measure)]['Variable'].values[0]

                # Fetch data
                df = fetch_data_in_batches([selected_var], API_KEY)
                
                # Debugging: Print the fetched data to ensure it was retrieved correctly
                st.write("Fetched Data:")
                st.write(df)

                if df is not None and not df.empty:
                    ranked_df = calculate_rankings(df, selected_var, rank_within_state, selected_state)
                    
                    # Debugging: Check the ranked dataframe
                    st.write("Ranked Data:")
                    st.write(ranked_df.head())

                    if not ranked_df.empty:
                        ranked_df['State Name'] = ranked_df['NAME'].str.split(',').str[-1].str.strip()
                        
                        # Display the dataframe
                        st.dataframe(ranked_df[['congressional district', 'State Name', 'Rank', selected_var]])

                        # Summary text
                        total_districts = ranked_df.shape[0]
                        selected_rank = ranked_df[ranked_df['NAME'] == district_name]['Rank'].values[0]
                        st.write(f"For your selected category '{category}' and measure '{measure}', the selected district ranks {int(selected_rank)} out of {total_districts} districts in the {'state' if rank_within_state else 'country'}.")
                    else:
                        st.warning("No ranking data found. Please ensure the selected measure has data for the chosen scope.")
                else:
                    st.warning("No data found for the selected measure. Please check the measure or try a different one.")
