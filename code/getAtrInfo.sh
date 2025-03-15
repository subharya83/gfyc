#!/bin/bash

# Function to display usage instructions
usage() {
    echo "Usage: $0 <URL>"
    echo "Example: $0 https://www.roadsideamerica.com/tip/10613"
    exit 1
}

# Function to extract attraction information
extract_attraction_info() {
    local url="$1"
    local html_content=$(curl -s "$url")

    # Extract the attraction name from the title tag
    local attraction_name=$(echo "$html_content" | grep -oP '(?<=<title>)[^<]+' | sed 's/ - Roadside America//')

    # Extract the address from the attractfacts div
    local address=$(echo "$html_content" | grep -A 10 'class="attractfacts"' | grep -oP '(?<=<a href="/map/10613">)[^<]+')

    # Extract the state from the title (e.g., "Albertville, AL")
    local state=$(echo "$attraction_name" | grep -oP '[A-Z]{2}')

    # Output the information in CSV format
    echo "\"$attraction_name\", \"$address\", \"$state\", \"$url\""
}

# Function to get latitude, longitude, and county from an address
get_geo_info() {
    local address="$1"
    local api_key="YOUR_OPENCAGE_API_KEY"  # Replace with your OpenCage API key
    local encoded_address=$(echo "$address" | jq -sRr @uri)  # URL-encode the address
    local api_url="https://api.opencagedata.com/geocode/v1/json?q=$encoded_address&key=$api_key"

    # Make the API call and parse the JSON response
    local response=$(curl -s "$api_url")
    local latitude=$(echo "$response" | jq -r '.results[0].geometry.lat')
    local longitude=$(echo "$response" | jq -r '.results[0].geometry.lng')
    local county=$(echo "$response" | jq -r '.results[0].components.county')

    # Output the information in CSV format
    echo "\"$address\", $latitude, $longitude, \"$county\""
}

# Main script logic
if [ $# -eq 0 ]; then
    usage
else
    # Extract attraction info
    attraction_info=$(extract_attraction_info "$1")
    echo "$attraction_info"

    # Extract address from the attraction info
    address=$(echo "$attraction_info" | awk -F'"' '{print $4}')

    # Get geo info for the address
    geo_info=$(get_geo_info "$address")
    echo "\"Address\", \"Latitude\", \"Longitude\", \"County\""
    echo "$geo_info"
fi