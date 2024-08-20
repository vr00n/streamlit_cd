import streamlit as st
import pandas as pd

# Load pre-fetched data
df = pd.read_csv('census_data.csv')

# Load the variables from the CSV file
variables_df = pd.read_csv('Variables.csv')

# Filter variables that end with "PE"
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

    variables_df[['Category', 'Measure']] = variables_df['Description'].apply(lambda x: pd.Series(extract_category_and_measure(x)))

    # Function to calculate rankings
    def calculate_rankings(df, var_code):
        if var_code in df.columns:
            df['Rank'] = df[var_code].rank(ascending=False)
        return df

    # Tab 1: ZIP code to Congressional District
    st.title("Find Your Congressional District Measures")

    zip_code = st.text_input("Enter your ZIP code:")

    if zip_code:
        # Map ZIP code to congressional district
        district_info = zip_to_district_df[zip_to_district_df['zip'] == int(zip_code)]
        if not district_info.empty:
            state_abbr = district_info['state_abbr'].values[0]
            district_number = district_info['district'].values[0]
            district_name = f"{state_abbr}-{district_number}"

            st.write(f"Congressional District: {district_name}")

            # Get the district data
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
