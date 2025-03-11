import argparse
import requests
import pandas as pd

# Base URL for the OpenCorporates API
BASE_URL = "https://api.opencorporates.com/v0.4/companies/search"

# API key (sign up at https://opencorporates.com/api to get a key)
API_KEY = "your_opencorporates_api_key_here"

def get_business_data(locations, fields):
    """
    Query the OpenCorporates API for registered businesses and their attributes.
    
    :param locations: List of locations (e.g., jurisdictions like "us_ny" for New York)
    :param fields: List of fields to retrieve (e.g., ['name', 'company_number', 'incorporation_date', 'status'])
    :return: DataFrame containing the requested data
    """
    data = []
    
    for location in locations:
        params = {
            'api_token': API_KEY,
            'jurisdiction_code': location,
            'fields': ','.join(fields)
        }
        
        response = requests.get(BASE_URL, params=params)
        if response.status_code == 200:
            business_data = response.json().get('results', {}).get('companies', [])
            for entry in business_data:
                company = entry.get('company', {})
                company['location'] = location  # Add location to each entry
                data.append(company)
        else:
            print(f"Failed to fetch data for location {location}: {response.status_code}")
    
    return pd.DataFrame(data)

def main():
    parser = argparse.ArgumentParser(description="Fetch registered business data from the OpenCorporates API.")
    parser.add_argument('--locations', nargs='+', required=True, help="List of jurisdictions (e.g., 'us_ny' for New York)")
    parser.add_argument('--output', required=True, help="Output CSV file path")
    
    args = parser.parse_args()
    
    # Define the fields to retrieve
    fields = ['name', 'company_number', 'incorporation_date', 'status']  # Add more fields as needed
    
    # Fetch the data
    df = get_business_data(args.locations, fields)
    
    # Write the data to a CSV file
    df.to_csv(args.output, index=False)
    print(f"Data written to {args.output}")

if __name__ == "__main__":
    main()

