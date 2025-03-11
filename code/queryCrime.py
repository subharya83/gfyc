import argparse
import requests
import pandas as pd
from datetime import datetime

# Base URL for the FBI Crime Data API
BASE_URL = "https://api.usa.gov/crime/fbi/cde/"

# API key (register at https://api.data.gov/signup/ to get a key)
API_KEY = "your_api_key_here"

def get_crime_data(county_codes, start_date, end_date, fields):
    """
    Query the FBI Crime Data API for monthly crime data for a list of county codes.
    
    :param county_codes: List of county codes (FIPS codes)
    :param start_date: Start date in 'YYYY-MM' format
    :param end_date: End date in 'YYYY-MM' format
    :param fields: List of fields to retrieve (e.g., ['violent_crime', 'theft'])
    :return: DataFrame containing the requested data
    """
    data = []
    
    for county_code in county_codes:
        url = f"{BASE_URL}county/{county_code}/offenses"
        params = {
            'api_key': API_KEY,
            'start_date': start_date,
            'end_date': end_date,
            'fields': ','.join(fields)
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            crime_data = response.json()
            for entry in crime_data:
                entry['county_code'] = county_code  # Add county code to each entry
            data.extend(crime_data)
        else:
            print(f"Failed to fetch data for county {county_code}: {response.status_code}")
    
    return pd.DataFrame(data)

def main():
    parser = argparse.ArgumentParser(description="Fetch monthly crime data from the FBI Crime Data API.")
    parser.add_argument('--counties', nargs='+', required=True, help="List of county FIPS codes")
    parser.add_argument('--start_date', required=True, help="Start date in 'YYYY-MM' format")
    parser.add_argument('--end_date', required=True, help="End date in 'YYYY-MM' format")
    parser.add_argument('--output', required=True, help="Output CSV file path")
    
    args = parser.parse_args()
    
    # Define the fields to retrieve
    fields = ['violent_crime', 'theft']  # Add more fields as needed
    
    # Fetch the data
    df = get_crime_data(args.counties, args.start_date, args.end_date, fields)
    
    # Write the data to a CSV file
    df.to_csv(args.output, index=False)
    print(f"Data written to {args.output}")

if __name__ == "__main__":
    main()
