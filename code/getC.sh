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
        
        # Parse the address into components (street, city, state, ZIP)
        street=$(echo "$input" | awk -F ',' '{print $1}' | sed 's/^ *//;s/ *$//')  # Extract street
        city_state_zip=$(echo "$input" | awk -F ',' '{print $2}' | sed 's/^ *//;s/ *$//')  # Extract city, state, ZIP
        city=$(echo "$city_state_zip" | awk -F ',' '{print $1}' | sed 's/^ *//;s/ *$//')  # Extract city
        state=$(echo "$city_state_zip" | awk -F ',' '{print $2}' | sed 's/^ *//;s/ *$//')  # Extract state
        zip=$(echo "$city_state_zip" | awk -F ',' '{print $3}' | sed 's/^ *//;s/ *$//')  # Extract ZIP

        # Debug: Print parsed address components
        echo "Debug - Parsed Address Components:"
        echo "Street: $street"
        echo "City: $city"
        echo "State: $state"
        echo "ZIP: $zip"

        # URL encode the components
        encoded_street=$(echo "$street" | jq -sRr @uri)
        encoded_city=$(echo "$city" | jq -sRr @uri)
        encoded_state=$(echo "$state" | jq -sRr @uri)
        encoded_zip=$(echo "$zip" | jq -sRr @uri)

        # Debug: Print URL-encoded components
        echo "Debug - URL-Encoded Components:"
        echo "Encoded Street: $encoded_street"
        echo "Encoded City: $encoded_city"
        echo "Encoded State: $encoded_state"
        echo "Encoded ZIP: $encoded_zip"

        # Build the URL with structured address components
        url="https://geocoding.geo.census.gov/geocoder/locations/address?street=${encoded_street}&city=${encoded_city}&state=${encoded_state}&zip=${encoded_zip}&benchmark=Public_AR_Current&format=json"

        # Debug: Print the constructed API URL
        echo "Debug - Constructed API URL:"
        echo "$url"
    fi

    # Make the API request
    echo "Debug - Making API request..."
    response=$(curl -s "$url")

    # Debug: Print the raw API response
    echo "Debug - Raw API Response:"
    echo "$response" | jq

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