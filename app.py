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

    # Create two tabs: one for finding congressional district measures by ZIP code and another for listing districts by measure
    tab1, tab2 = st.tabs(["Find District Measures by ZIP", "List Districts by Measure"])

    with tab1:
        st.title("Find Your Congressional District Measures")

        zip_code = st.text_input("Enter your ZIP code:")

        if zip_code:
            try:
                district_info = zip_to_district_df[zip_to_district_df['zip'] == int(zip_code)]
                if not district_info.empty:
                    state_fips = district_info['state_fips'].values[0]
                    district_number = district_info['district'].values[0]
                    
                    # Format the district number as an integer
                    district_number_int = int(district_number)

                    st.write(f"Mapped to state FIPS: {state_fips}, District: {district_number_int}")

                    district_df = df[(df['state'] == state_fips) & (df['congressional district'] == district_number_int)]

                    measures_data = []
                    valid_measures_count = 0

                    for _, row in variables_df.iterrows():
                        var_code = row['Variable']
                        category = row['Category']
                        measure_name = row['Measure']
                        
                        if var_code in district_df.columns:
                            measure_value = int(round(district_df[var_code].values[0]))
                            
                            if pd.notna(measure_value) and measure_value != -888888888:
                                ranked_df = calculate_rankings(df, var_code)
                                rank = int(ranked_df[(ranked_df['state'] == state_fips) & (ranked_df['congressional district'] == district_number_int)]['Rank'].values[0])
                                
                                measures_data.append({
                                    'Category': category,
                                    'Measure': measure_name,
                                    'Percentage of District Population': measure_value,
                                    'Rank': rank
                                })
                                valid_measures_count += 1
                            else:
                                continue
                        else:
                            st.write(f"Variable {var_code} not found in the district data. Skipping...")

                    st.write(f"Number of measures processed and included in the final table: {valid_measures_count}")

                    measures_df = pd.DataFrame(measures_data)

                    def highlight_row(row):
                        rank = int(row['Rank'])
                        if rank <= 10:
                            return ['background-color: lightgreen'] * len(row)
                        elif rank > len(df) - 10:
                            return ['background-color: lightcoral'] * len(row)
                        else:
                            return [''] * len(row)

                    st.dataframe(
                        measures_df.style.apply(highlight_row, axis=1),
                        use_container_width=True
                    )
                else:
                    st.warning("ZIP code not found in the database. Please try another.")
            except ValueError:
                st.error("Invalid ZIP code format. Please enter a valid ZIP code.")

    with tab2:
        st.title("List Congressional Districts by Measure")
    
        # Combine category and measure for the dropdown
        variables_df['Display'] = variables_df.apply(lambda x: f"{x['Category']}: {x['Measure']}", axis=1)
    
        # Dropdown for selecting a measure
        selected_display = st.selectbox(
            "Select a Measure",
            variables_df['Display'].unique()
        )
    
        if selected_display:
            # Find the variable code for the selected display
            selected_var = variables_df[variables_df['Display'] == selected_display]['Variable'].values[0]
            category = variables_df[variables_df['Display'] == selected_display]['Category'].values[0]
    
            st.write(f"Selected Measure: {selected_display} (Category: {category})")
    
            # Calculate rankings for all districts based on the selected measure
            ranked_df = calculate_rankings(df, selected_var)
    
            if not ranked_df.empty:
                # Map state FIPS and congressional district number to a readable format
                ranked_df['District'] = ranked_df.apply(lambda x: f"{zip_to_district_df.loc[zip_to_district_df['state_fips'] == x['state'], 'state_abbr'].values[0]}-{str(int(x['congressional district'])).zfill(2)}", axis=1)
                
                # Create hyperlinks for each district
                #ranked_df['District'] = ranked_df['District'].apply(lambda x: f"[{x}](https://datausa.io/profile/geo/congressional-district-{x.split('-')[1]}-{x.split('-')[0].lower()})")
    
                # Sort by rank
                ranked_df = ranked_df[['District', selected_var, 'Rank']].sort_values(by='Rank')
    
                # Rename columns for clarity
                ranked_df.columns = ['District', 'Measure Value', 'Rank']
    
                # Convert measure value and rank to integers
                ranked_df['Measure Value'] = ranked_df['Measure Value'].apply(lambda x: int(round(x)) if pd.notna(x) else x)
                ranked_df['Rank'] = ranked_df['Rank'].apply(lambda x: int(round(x)) if pd.notna(x) else x)
    
                # Display the dataframe with hyperlinks
                st.markdown(
                    ranked_df.to_markdown(index=False),
                    unsafe_allow_html=True
                )
            else:
                st.warning("No data found for the selected measure.")



