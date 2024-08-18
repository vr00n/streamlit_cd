import streamlit as st
import pandas as pd

# Load pre-fetched data
df = pd.read_csv('census_data.csv')

# Load the variables from the CSV file
variables_df = pd.read_csv('Variables.csv')

# Filter variables that end with "PE"
variables_df = variables_df[variables_df['Variable'].str.endswith("PE")]

if variables_df.empty or df.empty:
    st.error("Data could not be loaded. Please check the data files.")
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

    # Function to calculate rankings
    def calculate_rankings(df, var_code, rank_within_state=False, state_name=None):
        if rank_within_state and state_name is not None:
            state_name_to_code = {
                'Alabama': '01', 'Alaska': '02', 'Arizona': '04', 'Arkansas': '05', 'California': '06',
                # Add other states here...
            }
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
        sample_df = df[['NAME', 'state', 'congressional district', sample_var]].copy()

        if sample_df is not None:
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
                    ranked_df = calculate_rankings(df, selected_var, rank_within_state, selected_state)

                    if not ranked_df.empty:
                        ranked_df['State Name'] = ranked_df['NAME'].str.split(',').str[-1].str.strip()
                        st.dataframe(ranked_df[['congressional district', 'State Name', 'Rank', selected_var]])

                        total_districts = ranked_df.shape[0]
                        selected_rank = ranked_df[ranked_df['NAME'] == district_name]['Rank'].values[0]
                        st.write(f"For your selected category '{category}' and measure '{measure}', the selected district ranks {int(selected_rank)} out of {total_districts} districts in the {'state' if rank_within_state else 'country'}.")
                    else:
                        st.warning("No ranking data found. Please ensure the selected measure has data for the chosen scope.")

    with tab2:
        st.title("Top 10 Measures for Your Congressional District")

        if sample_df is not None:
            district_name = st.selectbox("Select Congressional District", congressional_districts, key="district_top10")

            if st.button("Show Top 10 Measures"):
                top_measures = []

                all_var_codes = variables_df['Variable'].unique()

                for var_code in all_var_codes:
                    ranked_df = calculate_rankings(df, var_code)
                    if not ranked_df.empty and district_name in ranked_df['NAME'].values:
                        district_rank = ranked_df[ranked_df['NAME'] == district_name]['Rank'].values[0]
                        if district_rank <= 10:
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
