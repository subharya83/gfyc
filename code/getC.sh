#!/bin/bash

# Function to get county name and optionally latitude/longitude
get_county() {
    input="$1"
    
    # Check if the input is a ZIP code (5 digits)
    if [[ $input =~ ^[0-9]{5}$ ]]; then
        echo "Looking up county for ZIP code: $input"
        url="https://geocoding.geo.census.gov/geocoder/locations/address?zip=${input}&benchmark=Public_AR_Current&format=json"
    else
        echo "Looking up county and coordinates for address: $input"
        # URL encode the address
        encoded_input=$(echo "$input" | jq -sRr @uri)
        url="https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=${encoded_input}&benchmark=Public_AR_Current&format=json"
    fi

    # Make the API request
    response=$(curl -s "$url")

    # Extract the county name using jq (JSON processor)
    county=$(echo "$response" | jq -r '.result.addressMatches[0].geographies.Counties[0].NAME')

    # Extract latitude and longitude if address is provided
    if [[ ! $input =~ ^[0-9]{5}$ ]]; then
        lat=$(echo "$response" | jq -r '.result.addressMatches[0].coordinates.y')
        lon=$(echo "$response" | jq -r '.result.addressMatches[0].coordinates.x')
    fi

    # Output results
    if [[ -z "$county" || "$county" == "null" ]]; then
        echo "No results found for the given input."
    else
        echo "County: $county"
        if [[ ! $input =~ ^[0-9]{5}$ ]]; then
            echo "Latitude: $lat"
            echo "Longitude: $lon"
        fi
    fi
}

# Check if input is provided
if [[ -z "$1" ]]; then
    echo "Usage: $0 <ZIP code or address>"
    exit 1
fi

# Call the function with the input
get_county "$1"