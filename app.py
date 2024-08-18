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

    # U.S. State Name to FIPS Code mapping
    state_name_to_code = {
        'Alabama': '01', 'Alaska': '02', 'Arizona': '04', 'Arkansas': '05', 'California': '06',
        'Colorado': '08', 'Connecticut': '09', 'Delaware': '10', 'District of Columbia': '11',
        'Florida': '12', 'Georgia': '13', 'Hawaii': '15', 'Idaho': '16', 'Illinois': '17',
        'Indiana': '18', 'Iowa': '19', 'Kansas': '20', 'Kentucky': '21', 'Louisiana': '22',
        'Maine': '23', 'Maryland': '24', 'Massachusetts': '25', 'Michigan': '26', 'Minnesota': '27',
        'Mississippi': '28', 'Missouri': '29', 'Montana': '30', 'Nebraska': '31', 'Nevada': '32',
        'New Hampshire': '33', 'New Jersey': '34', 'New Mexico': '35', 'New York': '36', 'North Carolina': '37',
        'North Dakota': '38', 'Ohio': '39', 'Oklahoma': '40', 'Oregon': '41', 'Pennsylvania': '42',
        'Rhode Island': '44', 'South Carolina': '45', 'South Dakota': '46', 'Tennessee': '47', 'Texas': '48',
        'Utah': '49', 'Vermont': '50', 'Virginia': '51', 'Washington': '53', 'West Virginia': '54',
        'Wisconsin': '55', 'Wyoming': '56'
    }

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
    def calculate_rankings(df, var_code, rank_within_state=False, state_name=None):
        if rank_within_state and state_name is not None:
            state_code = state_name_to_code.get(state_name)
            
            if state_code is not None:
                df = df[df['state'] == state_code]
                st.write(f"Filtered Data for state {state_name} (State Code: {state_code}):")
                st.write(df.head())  # Debugging
            else:
                st.warning(f"State code not found for the selected state: {state_name}")
                return df
            
            if df.empty:
                st.warning(f"No data found for the selected state: {state_name}. Please check the data or try a different state.")
                return df
        
        # Ensure we are ranking based on the correct variable column
        if var_code in df.columns:
            df['Rank'] = df[var_code].rank(ascending=False)
        else:
            st.error(f"Variable column '{var_code}' not found in the dataset.")
        
        return df

    # Create tabs for user interactions
    tab1, tab2 = st.tabs(["Compare Districts", "Top 10 Measures"])

    with tab1:
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

    with tab2:
        st.title("Top 10 Measures for Your Congressional District")

        if sample_df is not None:
            # Check for duplicates in the DataFrame
            if sample_df.duplicated().any():
                st.warning("Duplicate rows found in the data. Dropping duplicates.")
                sample_df = sample_df.drop_duplicates()
        
            # Ensure no duplicate columns (just in case)
            sample_df = sample_df.loc[:, ~sample_df.columns.duplicated()]
        
            # Now proceed with the rest of the logic
            district_name = st.selectbox("Select Congressional District", congressional_districts, key="district_top10")
        
            if st.button("Show Top 10 Measures"):
                top_measures = []
        
                # Fetch data for all variables in the dataset
                all_var_codes = variables_df['Variable'].unique()
                df = fetch_data_in_batches(all_var_codes, API_KEY)
        
                if df is not None and not df.empty:
                    for var_code in all_var_codes:
                        ranked_df = calculate_rankings(df, var_code)
                        if not ranked_df.empty:
                            # Check for duplicate rows and drop if any
                            if ranked_df.duplicated().any():
                                ranked_df = ranked_df.drop_duplicates()
        
                            # Check if the selected district is in the top 10
                            if district_name in ranked_df['NAME'].values:
                                district_rank = ranked_df[ranked_df['NAME'] == district_name]['Rank'].values[0]
                                if district_rank <= 10:
                                    # Get the measure associated with the variable
                                    measure = variables_df[variables_df['Variable'] == var_code]['Measure'].values[0]
                                    category = variables_df[variables_df['Variable'] == var_code]['Category'].values[0]
                                    top_measures.append({
                                        'Category': category,
                                        'Measure': measure,
                                        'Rank': district_rank
                                    })
        
                    if top_measures:
                        top_measures_df = pd.DataFrame(top_measures)
                        top_measures_df = top_measures_df.sort_values(by='Rank')
                        st.write(f"Top 10 Measures for {district_name}")
                        st.dataframe(top_measures_df)
                    else:
                        st.warning(f"No top 10 rankings found for {district_name}.")
                else:
                    st.warning("Failed to fetch data or data is empty.")
