import streamlit as st
import pandas as pd

# Load pre-fetched census data
df = pd.read_csv('census_data.csv')

# Load the variables from the CSV file
variables_df = pd.read_csv('Variables.csv')

# Filter variables that end with "PE" (percent estimate)
variables_df = variables_df[variables_df['Variable'].str.endswith("PE")]

# Load ZIP code to congressional district mapping
zip_to_district_df = pd.read_csv('zip_to_congressional_district.csv')

if variables_df.empty or df.empty or zip_to_district_df.empty:
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

    # Apply extraction of category and measure
    variables_df[['Category', 'Measure']] = variables_df['Description'].apply(lambda x: pd.Series(extract_category_and_measure(x)))

    # Function to calculate rankings within the dataset
    def calculate_rankings(df, var_code):
        if var_code in df.columns:
            df['Rank'] = df[var_code].rank(ascending=False)
        return df

    # Tab 1: ZIP code to Congressional District Mapping and Measures
    st.title("Find Your Congressional District Measures")

    zip_code = st.text_input("Enter your ZIP code:")

    if zip_code:
        # Convert ZIP code to int and map to congressional district
        try:
            district_info = zip_to_district_df[zip_to_district_df['zip'] == int(zip_code)]
            if not district_info.empty:
                state_abbr = district_info['state_abbr'].values[0]
                district_number = district_info['district'].values[0]
                district_name = f"{state_abbr}-{district_number}"

                st.write(f"Congressional District: {district_name}")

                # Filter the data for the selected district
                district_df = df[df['NAME'].str.contains(district_name, case=False)]

                if not district_df.empty:
                    measures_data = []
                    for _, row in variables_df.iterrows():
                        var_code = row['Variable']
                        category = row['Category']
                        measure_value = district_df[var_code].values[0]
                        ranked_df = calculate_rankings(df, var_code)
                        rank = ranked_df[ranked_df['NAME'] == district_name]['Rank'].values[0]
                        measures_data.append({'Category': category, 'Measure Value': measure_value, 'Rank': rank})

                    measures_df = pd.DataFrame(measures_data)

                    def highlight_row(row):
                        if row['Rank'] <= 10:
                            return ['background-color: lightgreen'] * len(row)
                        elif row['Rank'] > len(district_df) - 10:
                            return ['background-color: lightcoral'] * len(row)
                        else:
                            return [''] * len(row)

                    st.dataframe(measures_df.style.apply(highlight_row, axis=1))
                else:
                    st.warning("No data found for the selected ZIP code. Please try another.")
            else:
                st.warning("ZIP code not found in the database. Please try another.")
        except ValueError:
            st.error("Invalid ZIP code format. Please enter a valid ZIP code.")

    # Tab 2: Top 10 Measures for Congressional District (Same as previous tab 2 functionality)
    st.title("Top 10 Measures for Your Congressional District")

    if zip_code and not district_info.empty:
        if district_name:
            district_name = f"{state_abbr}-{district_number}"

            top_measures = []

            # Get all the percent estimate variables
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
