#!/bin/bash

# Function to get county name and FIPS code from latitude and longitude
get_county_from_coords() {
    lat="$1"
    lon="$2"
    # Build URL for Census Bureau Geocoding Services API (reverse geocoding)
    url="https://geocoding.geo.census.gov/geocoder/geographies/coordinates?x=${lon}&y=${lat}&benchmark=Public_AR_Current&vintage=Current_Current&format=json"
    response=$(curl -s "$url")
    
    # Extract county info from response
    county_name=$(echo "$response" | jq -r '.result.geographies.Counties[0].NAME')
    county_fips=$(echo "$response" | jq -r '.result.geographies.Counties[0].GEOID')
    state_name=$(echo "$response" | jq -r '.result.geographies.States[0].NAME')
    state_fips=$(echo "$response" | jq -r '.result.geographies.States[0].GEOID')
    
    # Check if we got valid results
    if [[ -z "$county_name" || "$county_name" == "null" ]]; then
        echo "No county found for the given coordinates."
        return 1
    else
        # Output the results
        echo "County: $county_name"
        echo "County FIPS: $county_fips"
        echo "State: $state_name"
        echo "State FIPS: $state_fips"
        return 0
    fi
}

# Updated get_county function to use coordinates when available
get_county() {
    input="$1"
    
    # Check if the input is a ZIP code (5 digits)
    if [[ $input =~ ^[0-9]{5}$ ]]; then
        url="https://geocoding.geo.census.gov/geocoder/locations/address?zip=${input}&benchmark=Public_AR_Current&format=json"
        
        # Make the API request
        response=$(curl -s "$url")
        
        # Extract coordinates
        lat=$(echo "$response" | jq -r '.result.addressMatches[0].coordinates.y')
        lon=$(echo "$response" | jq -r '.result.addressMatches[0].coordinates.x')
        
        if [[ -z "$lat" || "$lat" == "null" || -z "$lon" || "$lon" == "null" ]]; then
            echo "Could not get coordinates for ZIP code $input."
            return 1
        fi
        # Get county from coordinates
        get_county_from_coords "$lat" "$lon"
        
    else
        echo "Looking up county and coordinates for address: $input"
        
        # Parse the address into components
        # First split by comma to get street vs the rest
        street=$(echo "$input" | awk -F ',' '{print $1}' | sed 's/^ *//;s/ *$//')
        
        # Get the remaining parts (city, state, ZIP)
        remainder=$(echo "$input" | cut -d ',' -f 2- | sed 's/^ *//;s/ *$//')
        
        # Extract city (second comma-separated value)
        city=$(echo "$remainder" | awk -F ',' '{print $1}' | sed 's/^ *//;s/ *$//')
        
        # Extract state (third comma-separated value)
        state=$(echo "$remainder" | awk -F ',' '{print $2}' | sed 's/^ *//;s/ *$//')
        
        # Extract ZIP (fourth comma-separated value, or last part)
        zip=$(echo "$remainder" | awk -F ',' '{print $3}' | sed 's/^ *//;s/ *$//')

        # URL encode the components
        encoded_street=$(echo "$street" | jq -sRr @uri)
        encoded_city=$(echo "$city" | jq -sRr @uri)
        encoded_state=$(echo "$state" | jq -sRr @uri)
        
        # Build the URL with structured address components
        # Only include ZIP in the URL if it's not empty
        if [[ -z "$zip" ]]; then
            url="https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=${encoded_street},${encoded_city},${encoded_state}&benchmark=Public_AR_Current&format=json"
        else
            encoded_zip=$(echo "$zip" | jq -sRr @uri)
            url="https://geocoding.geo.census.gov/geocoder/locations/address?street=${encoded_street}&city=${encoded_city}&state=${encoded_state}&zip=${encoded_zip}&benchmark=Public_AR_Current&format=json"
        fi
        
        response=$(curl -s "$url")
        
        # Debug the API response
        if [[ -z "$(echo "$response" | jq -r '.result.addressMatches[0]')" || "$(echo "$response" | jq -r '.result.addressMatches[0]')" == "null" ]]; then
            echo "API returned no matches. Using one-line address format instead."
            # Try alternative format with one-line address
            encoded_address=$(echo "$input" | jq -sRr @uri)
            url="https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=${encoded_address}&benchmark=Public_AR_Current&format=json"
            response=$(curl -s "$url")
        fi
        
        # Extract coordinates
        lat=$(echo "$response" | jq -r '.result.addressMatches[0].coordinates.y')
        lon=$(echo "$response" | jq -r '.result.addressMatches[0].coordinates.x')
        
        if [[ -z "$lat" || "$lat" == "null" || -z "$lon" || "$lon" == "null" ]]; then
            echo "Could not get coordinates for address: $input"
            return 1
        fi
        
        echo "Coordinates found - Latitude: $lat, Longitude: $lon"
        
        # Get county from coordinates
        get_county_from_coords "$lat" "$lon"
    fi
}

# Standalone function to be called directly with coordinates
get_county_info() {
    if [[ $# -lt 2 ]]; then
        echo "Usage: get_county_info <latitude> <longitude>"
        return 1
    fi
    
    get_county_from_coords "$1" "$2"
}

# Check if input is provided
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <ZIP code or address>"
    echo "   OR: $0 --coords <latitude> <longitude>"
    exit 1
fi

# Parse command line arguments
if [[ "$1" == "--coords" && $# -eq 3 ]]; then
    # Use coordinates directly
    get_county_from_coords "$2" "$3"
else
    # Use address or ZIP code
    get_county "$*"
fi