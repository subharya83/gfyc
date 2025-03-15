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

    # Extract the address from the attractfacts div using sed
    local address=$(echo "$html_content" | sed -n '/class="attractfacts"/,/<\/div>/p' | grep -oP '(?<=<a href="/map/[0-9]+">)[^<]+')

    # Extract the state from the title (e.g., "Albertville, AL")
    local state=$(echo "$attraction_name" | grep -oP '[A-Z]{2}')

    # Output the information in CSV format
    echo "\"$attraction_name\", \"$address\", \"$state\", \"$url\""
}

# Function to get latitude, longitude, county, and formatted address from an address using Google Maps API
get_geo_info() {
    local address="$1"
    local api_key="AIzaSyCUfXqvurEH_EMMahJUoajN1tkR4HCdUDk"  # Replace with your Google Maps API key
    local encoded_address=$(echo "$address" | jq -sRr @uri)  # URL-encode the address
    local api_url="https://maps.googleapis.com/maps/api/geocode/json?address=$encoded_address&key=$api_key"

    # Make the API call and parse the JSON response
    local response=$(curl -s "$api_url")
    local latitude=$(echo "$response" | jq -r '.results[0].geometry.location.lat')
    local longitude=$(echo "$response" | jq -r '.results[0].geometry.location.lng')
    local county=$(echo "$response" | jq -r '.results[0].address_components[] | select(.types[] == "administrative_area_level_2") | .long_name')
    local formatted_address=$(echo "$response" | jq -r '.results[0].formatted_address')

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