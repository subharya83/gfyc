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

    # Extract the state from the URL
    local state=$(echo "$url" | awk -F'/' '{print $5}' | tr '[:lower:]' '[:upper:]')

    # Output the information in CSV format
    echo "\"$attraction_name\", \"$address\", \"$state\", \"$url\""
}

# Main script logic
if [ $# -eq 0 ]; then
    usage
else
    extract_attraction_info "$1"
fi