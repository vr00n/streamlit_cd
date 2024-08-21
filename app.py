import streamlit as st
import pandas as pd
from openai import OpenAI


st.set_page_config(layout="wide")

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

# State FIPS to state name mapping
state_fips_to_name = {
    '01': 'Alabama', '02': 'Alaska', '04': 'Arizona', '05': 'Arkansas', '06': 'California',
    '08': 'Colorado', '09': 'Connecticut', '10': 'Delaware', '11': 'District of Columbia',
    '12': 'Florida', '13': 'Georgia', '15': 'Hawaii', '16': 'Idaho', '17': 'Illinois',
    '18': 'Indiana', '19': 'Iowa', '20': 'Kansas', '21': 'Kentucky', '22': 'Louisiana',
    '23': 'Maine', '24': 'Maryland', '25': 'Massachusetts', '26': 'Michigan', '27': 'Minnesota',
    '28': 'Mississippi', '29': 'Missouri', '30': 'Montana', '31': 'Nebraska', '32': 'Nevada',
    '33': 'New Hampshire', '34': 'New Jersey', '35': 'New Mexico', '36': 'New York',
    '37': 'North Carolina', '38': 'North Dakota', '39': 'Ohio', '40': 'Oklahoma', '41': 'Oregon',
    '42': 'Pennsylvania', '44': 'Rhode Island', '45': 'South Carolina', '46': 'South Dakota',
    '47': 'Tennessee', '48': 'Texas', '49': 'Utah', '50': 'Vermont', '51': 'Virginia',
    '53': 'Washington', '54': 'West Virginia', '55': 'Wisconsin', '56': 'Wyoming'
}

# Initialize OpenAI client using st.secrets for the API key
client = OpenAI(api_key=st.secrets["openai"]["api_key"])


def get_openai_chat_response(data):
    response = client.chat.completions.create(
        model="gpt-4o",  # Use the GPT-4o chat model
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Based on the following measures: {data}, describe the typical household from a political perspective for someone running for Congress."},
        ],
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()

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
                    state_fips = str(district_info['state_fips'].values[0]).zfill(2)
                    district_number = district_info['district'].values[0]
                    
                    # Format the district number as an integer
                    district_number_int = int(district_number)

                    # Get state name from FIPS
                    state_name = state_fips_to_name.get(state_fips, "Unknown")

                    # Construct readable district name
                    district_name_readable = f"{state_name} {district_number_int}th"

                    st.write(f"Your congressional district is {district_name_readable}.")

                    district_df = df[(df['state'] == int(state_fips)) & (df['congressional district'] == district_number_int)]

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
                                rank = int(ranked_df[(ranked_df['state'] == int(state_fips)) & (ranked_df['congressional district'] == district_number_int)]['Rank'].values[0])
                                
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
                        use_container_width=True, hide_index=True
                    )

                    # Convert measures_df to a format that can be passed to the OpenAI API
                    measures_dict = measures_df.to_dict(orient='records')
                    # Pass the DataFrame content to the OpenAI API and get the response
                    openai_response = get_openai_chat_response(measures_dict)

                    # Display the OpenAI API response in Tab 1
                    st.subheader("Political Perspective Based on Measures")
                    st.write(openai_response)
                else:
                    st.warning("ZIP code not found in the database. Please try another.")
            except ValueError:
                st.error("Invalid ZIP code format. Please enter a valid ZIP code.")

    with tab2:
        st.title("List Congressional Districts by Measure")

        # Combine category and measure for the dropdown
        variables_df['Display'] = variables_df.apply(lambda x: f"{x['Category']}: {x['Measure']}", axis=1)

        # Sort the options alphabetically
        sorted_options = sorted(variables_df['Display'].unique())

        # Create a dropdown for selecting a measure
        selected_display = st.selectbox(
            "Select a Measure",
            sorted_options
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
                ranked_df['District'] = ranked_df['District'].apply(lambda x: f"[{x}](https://datausa.io/profile/geo/congressional-district-{x.split('-')[1]}-{x.split('-')[0].lower()})")
    
                # Sort by rank
                ranked_df = ranked_df[['District', selected_var, 'Rank']].sort_values(by='Rank')
    
                # Rename columns for clarity
                ranked_df.columns = ['District', 'Measure Value', 'Rank']
    
                # Convert measure value and rank to integers
                ranked_df['Measure Value'] = ranked_df['Measure Value'].apply(lambda x: int(round(x)) if pd.notna(x) else x)
                ranked_df['Rank'] = ranked_df['Rank'].apply(lambda x: int(round(x)) if pd.notna(x) else x)
    
                # Display the dataframe with hyperlinks
                st.data_editor(
                    ranked_df,
                    column_config={
                        "District": st.column_config.LinkColumn("District"),
                        "Measure Value": "Measure Value",
                        "Rank": "Rank"
                    },
                    hide_index=True,
                )
            else:
                st.warning("No data found for the selected measure.")
