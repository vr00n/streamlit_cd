import streamlit as st
import pandas as pd

# Load pre-fetched census data
df = pd.read_csv('census_data.csv')

# Load the variables from the CSV file
variables_df = pd.read_csv('Variables.csv')

# Filter variables that end with "PE" (percent estimate) and are of type 'Percent'
variables_df = variables_df[(variables_df['Variable'].str.endswith("PE")) & (variables_df['P_or_E'] == 'Percent')]

# Exclude measures where the category is "SELECTED SOCIAL CHARACTERISTICS IN PUERTO RICO"
variables_df = variables_df[variables_df['Category'] != 'SELECTED SOCIAL CHARACTERISTICS IN PUERTO RICO']

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

    # Debugging: Print initial number of measures
    st.write(f"Initial number of measures in Variables.csv: {len(variables_df)}")

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

                # Debugging: Report the number of variables in the district_df
                st.write(f"Number of variables in district_df: {district_df.shape[1] - 2}")

                measures_data = []
                valid_measures_count = 0

                for _, row in variables_df.iterrows():
                    var_code = row['Variable']
                    category = row['Category']
                    measure_name = row['Measure']
                    
                    if var_code in district_df.columns:
                        measure_value = district_df[var_code].values[0]
                        
                        # Check for invalid data
                        if pd.notna(measure_value) and measure_value != -888888888:
                            ranked_df = calculate_rankings(df, var_code)
                            rank = ranked_df[(ranked_df['state'] == state_fips) & (ranked_df['congressional district'] == district_number_int)]['Rank'].values[0]
                            
                            measures_data.append({
                                'Category': category,
                                'Measure': measure_name,
                                'Percentage of District Population': str(int(round(measure_value))),
                                'Rank': str(int(round(rank)))
                            })
                            valid_measures_count += 1
                        else:
                            continue
                    else:
                        st.write(f"Variable {var_code} not found in the district data. Skipping...")

                # Debugging: Report the final count of valid measures
                st.write(f"Number of measures processed and included in the final table: {valid_measures_count}")

                measures_df = pd.DataFrame(measures_data)

                # Only include measures that have percent values
                measures_df = measures_df[measures_df['Percentage of District Population'] != '-888888888']

                def highlight_row(row):
                    rank = int(row['Rank'])
                    if rank <= 10:
                        return ['background-color: lightgreen'] * len(row)
                    elif rank > len(df) - 10:
                        return ['background-color: lightcoral'] * len(row)
                    else:
                        return [''] * len(row)

                # Set table width and length
                st.dataframe(
                    measures_df.style.apply(highlight_row, axis=1),
                    use_container_width=True
                )
            else:
                st.warning("ZIP code not found in the database. Please try another.")
        except ValueError:
            st.error("Invalid ZIP code format. Please enter a valid ZIP code.")
