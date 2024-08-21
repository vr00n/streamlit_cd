import streamlit as st
import pandas as pd

# Load pre-fetched census data
df = pd.read_csv('census_data.csv')

# De-duplicate columns in the census data
df = df.loc[:, ~df.columns.duplicated()]

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

                if not district_df.empty:
                    measures_data = []
                    for _, row in variables_df.iterrows():
                        var_code = row['Variable']
                        category = row['Category']
                        measure_name = row['Measure']
                        
                        measure_value = district_df[var_code].values[0] if pd.notna(district_df[var_code].values[0]) else None
                        ranked_df = calculate_rankings(df, var_code)

                        # Filter out invalid measure values and NaNs
                        if measure_value is None or measure_value == -888888888:
                            continue

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

                    # Set table width to 100% and ensure the table fits within the container
                    st.dataframe(
                        measures_df.style.apply(highlight_row, axis=1),
                        use_container_width=True
                    )
                else:
                    st.warning("No data found for the selected ZIP code. Please try another.")
            else:
                st.warning("ZIP code not found in the database. Please try another.")
        except ValueError:
            st.error("Invalid ZIP code format. Please enter a valid ZIP code.")
