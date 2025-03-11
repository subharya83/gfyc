import argparse
import requests
import pandas as pd
from datetime import datetime

# Base URL for the weather API (replace with the actual API endpoint)
BASE_URL = "https://api.weather.gov/"

# API key (if required, replace with your actual API key)
API_KEY = "your_api_key_here"

def get_weather_data(county_codes, start_date, end_date, fields):
    """
    Query the weather database for monthly weather data for a list of county codes.
    
    :param county_codes: List of county codes
    :param start_date: Start date in 'YYYY-MM' format
    :param end_date: End date in 'YYYY-MM' format
    :param fields: List of fields to retrieve (e.g., ['temperature', 'rainfall', 'humidity', 'wind', 'air_quality'])
    :return: DataFrame containing the requested data
    """
    data = []
    
    for county_code in county_codes:
        url = f"{BASE_URL}county/{county_code}/weather"
        params = {
            'key': API_KEY,
            'fields': ','.join(fields),
            'start_date': start_date,
            'end_date': end_date
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            weather_data = response.json()
            data.extend(weather_data)
        else:
            print(f"Failed to fetch data for county {county_code}: {response.status_code}")
    
    return pd.DataFrame(data)

def main():
    parser = argparse.ArgumentParser(description="Fetch monthly weather data from the US weather database.")
    parser.add_argument('--counties', nargs='+', required=True, help="List of county codes")
    parser.add_argument('--start_date', required=True, help="Start date in 'YYYY-MM' format")
    parser.add_argument('--end_date', required=True, help="End date in 'YYYY-MM' format")
    parser.add_argument('--output', required=True, help="Output CSV file path")
    
    args = parser.parse_args()
    
    # Define the fields to retrieve
    fields = ['temperature', 'rainfall', 'humidity', 'wind', 'air_quality']
    
    # Fetch the data
    df = get_weather_data(args.counties, args.start_date, args.end_date, fields)
    
    # Write the data to a CSV file
    df.to_csv(args.output, index=False)
    print(f"Data written to {args.output}")

if __name__ == "__main__":
    main()

