# Census Data Explorer

This Streamlit application allows users to explore and rank U.S. Congressional Districts based on various measures from the Census Bureau's ACS (American Community Survey) data. The application provides three primary functionalities:

1. **Rank Congressional Districts**: Fetch and rank data for specific variables across all Congressional Districts.
2. **Top N Districts by Measure**: Display the top N Congressional Districts for a selected measure.
3. **Top 10 Measures for a District**: Identify and display the top 10 measures where a selected Congressional District ranks among the top 10 nationwide.

## Features

- **Batch Data Fetching**: The app fetches data in batches to optimize API requests and reduce load time.
- **Parallel Processing**: Utilizes multithreading to process variable rankings in parallel, improving performance.
- **Exponential Backoff**: Implements a retry mechanism with exponential backoff for handling API request failures.
- **User-Friendly Interface**: Includes search functionality for easy variable selection, as well as customizable ranking views.

## Requirements

- Python 3.7 or higher
- Streamlit
- Pandas
- Requests

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/census-data-explorer.git
    cd census-data-explorer
    ```

2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Create a CSV file named `Variables.csv` in the project root with the following structure:
    ```csv
    Variable,Description
    B01001_001E,Total Population
    B02001_002
