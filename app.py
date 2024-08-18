import streamlit as st
import pandas as pd
import requests
import time
from concurrent.futures import ThreadPoolExecutor

# Load the variables from the CSV file
variables_df = pd.read_csv('Variables.csv')

# Filter variables that end with "PE"
variables_df = variables_df[variables_df['Variable'].str.endswith("PE")]

if variables_df.empty:
    st.error("No variables found ending with 'PE'. Please check the CSV file.")
else:
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

    API_KEY = 'fd901c69fb4729a262b7e163c1db69737513827d'

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

    def fetch_data_in_batches(variables, api_key, batch_size=10, retries=3, timeout=10):
        batched_variables = [variables[i:i + batch_size] for i in range(0, len(variables), batch_size)]
        full_df = pd.DataFrame()

        def fetch_batch(batch):
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
                        return df
                except requests.exceptions.RequestException:
                    time.sleep(2 ** attempt)
            return pd.DataFrame()  # Return an empty DataFrame on failure

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(fetch_batch, batched_variables))
        
        full_df = pd.concat(results, axis=1)
        return full_df

    def calculate_rankings(df, var_code, rank_within_state=False, state_name=None):
        if rank_within_state and state_name is not None:
            state_code = state_name_to_code.get(state_name)
            if state_code:
                df = df[df['state'] == state_code]
            if df.empty:
                return df
        
        if var_code in df.columns:
            df['Rank'] = df[var_code].rank(ascending=False)
        return df

    tab1, tab2 = st.tabs(["Compare Districts", "Top 10 Measures"])

    with tab1:
        sample_var = variables_df.iloc[0]['Variable']
        sample_df = fetch_data_in_batches([sample_var], API_KEY)

        if sample_df is not None:
            sample_df = sample_df.drop_duplicates()
            sample_df = sample_df.loc[:, ~sample_df.columns.duplicated()]

            sample_df['District Name'] = sample_df['NAME'].str.strip()
            congressional_districts = sample_df['District Name'].unique()

            st.title("Compare Your Congressional District")
            st.markdown("**Start by selecting your Congressional District**")

            district_name = st.selectbox("Select Congressional District", congressional_districts)

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

                ranking_scope = st.radio("Rank within:", ['State', 'Nation'])

                if st.button("Fetch and Compare"):
                    rank_within_state = (ranking_scope == 'State')
                    selected_state = district_name.split(',')[-1].strip()

                    selected_var = variables_df[(variables_df['Category'] == category) & (variables_df['Measure'] == measure)]['Variable'].values[0]
                    df = fetch_data_in_batches([selected_var], API_KEY)

                    df = df.drop_duplicates()
                    df = df.loc[:, ~df.columns.duplicated()]

                    if df is not None and not df.empty:
                        ranked_df = calculate_rankings(df, selected_var, rank_within_state, selected_state)
                        
                        if not ranked_df.empty:
                            ranked_df['State Name'] = ranked_df['NAME'].str.split(',').str[-1].str.strip()
                            st.dataframe(ranked_df[['congressional district', 'State Name', 'Rank', selected_var]])

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
            district_name = st.selectbox("Select Congressional District", congressional_districts, key="district_top10")

            if st.button("Show Top 10 Measures"):
                top_measures = []

                all_var_codes = variables_df['Variable'].unique()

                def process_var(var_code):
                    df = fetch_data_in_batches([var_code], API_KEY)
                    df = df.drop_duplicates()
                    df = df.loc[:, ~df.columns.duplicated()]

                    ranked_df = calculate_rankings(df, var_code)
                    ranked_df = ranked_df.drop_duplicates()
                    ranked_df = ranked_df.loc[:, ~ranked_df.columns.duplicated()]

                    if district_name in ranked_df['NAME'].values:
                        district_rank = ranked_df[ranked_df['NAME'] == district_name]['Rank'].values[0]
                        if district_rank <= 10:
                            measure = variables_df[variables_df['Variable'] == var_code]['Measure'].values[0]
                            category = variables_df[variables_df['Variable'] == var_code]['Category'].values[0]
                            return {
                                'Category': category,
                                'Measure': measure,
                                'Rank': district_rank
                            }
                    return None

                with ThreadPoolExecutor() as executor:
                    results = list(executor.map(process_var, all_var_codes))
                
                top_measures = [result for result in results if result is not None]

                if top_measures:
                    top_measures_df = pd.DataFrame(top_measures)
                    top_measures_df = top_measures_df.sort_values(by='Rank')
                    st.write(f"Top 10 Measures for {district_name}")
                    st.dataframe(top_measures_df)
                else:
                    st.warning(f"No top 10 rankings found for {district_name}.")
