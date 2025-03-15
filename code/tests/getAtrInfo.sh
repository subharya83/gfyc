#!/bin/bash

# Function to display usage instructions
usage() {
    echo "Usage: $0 <URL>"
    echo "Example: $0 https://www.roadsideamerica.com/tip/10613"
    exit 1
}

# Function to sanitize text by removing newlines and extra spaces
sanitize() {
    echo "$1" | tr -d '\n\r' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//'
}

# Function to extract attraction information
extract_attraction_info() {
    local url="$1"
    local html_content=$(curl -s "$url")

    # Extract the attraction name from the title tag
    local attraction_name=$(echo "$html_content" | grep -o '<title>[^<]*' | sed 's/<title>//' | sed 's/ - Roadside America//')
    attraction_name=$(sanitize "$attraction_name")

    # Extract the address using a more robust method
    local address=$(echo "$html_content" | grep -A3 '<dt>Address:</dt>' | grep -o '<a href="/map/[^>]*>[^<]*' | sed 's/.*">//')
    
    # If address is empty, try another method
    if [ -z "$address" ]; then
        address=$(echo "$html_content" | grep -A3 '<dt>Address:</dt>' | grep -o '<dd><a href="/map/[^>]*>[^<]*' | sed 's/.*">//')
    fi
    address=$(sanitize "$address")

    # Extract the state from the title (e.g., "Albertville, AL")
    local state=$(echo "$attraction_name" | grep -o '[A-Z][A-Z]$')
    state=$(sanitize "$state")

    # Output the information in CSV format
    echo "\"$attraction_name\", \"$address\", \"$state\", \"$url\""
}

# Function to get latitude, longitude, county, and formatted address from an address using Google Maps API
get_geo_info() {
    local address="$1"
    local api_key="API_KEY"  # Replace with your Google Maps API key
    local encoded_address=$(echo "$address" | jq -sRr @uri)  # URL-encode the address
    local api_url="https://maps.googleapis.com/maps/api/geocode/json?address=$encoded_address&key=$api_key"

    # Make the API call and parse the JSON response
    local response=$(curl -s "$api_url")
    local latitude=$(echo "$response" | jq -r '.results[0].geometry.location.lat')
    latitude=$(sanitize "$latitude")
    
    local longitude=$(echo "$response" | jq -r '.results[0].geometry.location.lng')
    longitude=$(sanitize "$longitude")
    
    local county=$(echo "$response" | jq -r '.results[0].address_components[] | select(.types[] == "administrative_area_level_2") | .long_name')
    county=$(sanitize "$county")
    
    local formatted_address=$(echo "$response" | jq -r '.results[0].formatted_address')
    formatted_address=$(sanitize "$formatted_address")

    echo "\"$latitude\", \"$longitude\", \"$county\", \"$formatted_address\""
}

# Main script logic
if [ $# -eq 0 ]; then
    usage
else
    # Extract attraction info
    _att=$(extract_attraction_info "$1")
    # Extract address from the attraction info
    address=$(echo "$_att" | awk -F'"' '{print $4}')

    # Get geo info for the address
    if [ -n "$address" ]; then
        _geo=$(get_geo_info "$address")
        echo "$_att,$_geo"
    else
        echo "$_att,\"\", \"\", \"\", \"\""
    fi
fi