import streamlit as st
import pandas as pd

# Load pre-fetched census data
df = pd.read_csv('census_data.csv')

# De-duplicate columns in the census data
df = df.loc[:, ~df.columns.duplicated()]

# Load the variables from the CSV file
variables_df = pd.read_csv('Variables.csv')

# Debugging: Report the initial number of measures in Variables.csv
initial_measure_count = variables_df.shape[0]
st.write(f"Initial number of measures in Variables.csv: {initial_measure_count}")

# Filter variables that end with "PE"
variables_df = variables_df[variables_df['Variable'].str.endswith("PE")]
st.write(f"Number of measures after filtering for 'PE': {variables_df.shape[0]}")

# Further filter variables that have "Percent" in the P_or_E column
variables_df = variables_df[variables_df['P_or_E'] == 'Percent']
st.write(f"Number of measures after filtering for 'Percent': {variables_df.shape[0]}")

# Exclude variables where Category equals "SELECTED SOCIAL CHARACTERISTICS IN PUERTO RICO"
variables_df = variables_df[variables_df['Category'] != "SELECTED SOCIAL CHARACTERISTICS IN PUERTO RICO"]
st.write(f"Number of measures after excluding Puerto Rico-related measures: {variables_df.shape[0]}")

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

    # Main Section: ZIP code to Congressional District Mapping and Measures
    st.title("Find Your Congressional District Measures")

    zip_code = st.text_input("Enter your ZIP code:")

    if zip_code:
        # Convert ZIP code to int and map to congressional district
        try:
            district_info = zip_to_district_df[zip_to_district_df['zip'] == int(zip_code)]
            if not district_info.empty:
                state_fips = district_info['state_fips'].values[0]
                district_number = district_info['district'].values[0]
                
                # Format the district number as an integer
                district_number_int = int(district_number)

                st.write(f"Mapped to state FIPS: {state_fips}, District: {district_number_int}")

                # Filter the data for the selected district using state and congressional district
                district_df = df[(df['state'] == state_fips) & (df['congressional district'] == district_number_int)]

                st.write(f"Number of variables in district_df: {district_df.shape[1] - 2}")  # Subtract 2 for the 'state' and 'congressional district' columns

                if not district_df.empty:
                    measures_data = []
                    processed_count = 0

                    for _, row in variables_df.iterrows():
                        var_code = row['Variable']
                        category = row['Category']
                        measure_name = row['Measure']
                        
                        # Check if the variable exists in the data
                        if var_code not in district_df.columns:
                            st.warning(f"Variable {var_code} not found in the census data. Skipping...")
                            continue

                        measure_value = district_df[var_code].values[0] if pd.notna(district_df[var_code].values[0]) else None
                        ranked_df = calculate_rankings(df, var_code)

                        # Filter out invalid measure values and NaNs
                        if measure_value is None or measure_value == -888888888:
                            continue

                        processed_count += 1  # Count the number of measures that pass the filters

                        # Safely handle rounding and converting measure_value and rank to string
                        measure_value = str(int(round(measure_value))) if pd.notna(measure_value) else 'N/A'
                        rank = ranked_df[(ranked_df['state'] == state_fips) & (ranked_df['congressional district'] == district_number_int)]['Rank'].values[0]
                        rank = str(int(round(rank))) if pd.notna(rank) else 'N/A'

                        measures_data.append({
                            'Category': category,
                            'Measure': measure_name,
                            'Percentage of District Population': measure_value,
                            'Rank': rank
                        })

                    st.write(f"Number of measures processed and included in the final table: {processed_count}")

                    measures_df = pd.DataFrame(measures_data)

                    # Only include measures that have percent values
                    measures_df = measures_df[measures_df['Measure'].str.contains('percent', case=False, na=False)]

                    def highlight_row(row):
                        if row['Rank'] != 'N/A' and int(row['Rank']) <= 10:
                            return ['background-color: lightgreen'] * len(row)
                        elif row['Rank'] != 'N/A' and int(row['Rank']) > len(df) - 10:
                            return ['background-color: lightcoral'] * len(row)
                        else:
                            return [''] * len(row)
                    
                    # Debugging: Check the contents of the measures_df before displaying
                    st.write("Contents of measures_df:", measures_df)

                    # Set table width to 100% and ensure the table fits within the container
                    st.dataframe(
                        measures_df.style.apply(highlight_row, axis=1),
                        use_container_width=True,
                        height=1000  # Adjust height as needed to show more rows
                    )
                else:
                    st.warning("No data found for the selected ZIP code. Please try another.")
            else:
                st.warning("ZIP code not found in the database. Please try another.")
        except ValueError:
            st.error("Invalid ZIP code format. Please enter a valid ZIP code.")
