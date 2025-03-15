#!/bin/bash

states=('AL' 'AK' 'AZ' 'AR' 'CA' 'CO' 'CT' 'DE' 'DC' 'FL' 'GA' 'HI' 'ID' 'IL' 
 'IN' 'IA' 'KS' 'KY' 'LA' 'ME' 'MD' 'MA' 'MI' 'MN' 'MS' 'MO' 'MT' 'NE' 'NV' 
 'NH' 'NJ' 'NM' 'NY' 'NC' 'ND' 'OH' 'OK' 'OR' 'PA' 'PR' 'RI' 'SC' 'SD' 'TN' 
 'TX' 'UT' 'VT' 'VI' 'VA' 'WA' 'WV' 'WI' 'WY')

urlbase='https://www.roadsideamerica.com/'

# Function to display usage
usage() {
    echo "Usage: $0 -o <output_directory>"
    echo "This script retrieves a list of attractions for each state and saves the details into a file."
    echo "Options:"
    echo "  -o <output_directory>  Specify the output directory for saving files."
    exit 1
}

# Function to handle errors
handle_error() {
    echo "Error: $1"
    exit 1
}

# Function to get county name and FIPS code from latitude and longitude
get_county_from_coords() {
    local lat="$1"
    local lon="$2"
    
    # Build URL for Census Bureau Geocoding Services API (reverse geocoding)
    local url="https://geocoding.geo.census.gov/geocoder/geographies/coordinates?x=${lon}&y=${lat}&benchmark=Public_AR_Current&vintage=Current_Current&format=json"
    local response=$(curl -s "$url")
    
    # Extract county info from response
    local county_name=$(echo "$response" | jq -r '.result.geographies.Counties[0].NAME')
    local county_fips=$(echo "$response" | jq -r '.result.geographies.Counties[0].GEOID')
    
    # Check if we got valid results
    if [[ -z "$county_name" || "$county_name" == "null" ]]; then
        echo "N/A|N/A"
    else
        # Output the results in format county|fips
        echo "$county_name|$county_fips"
    fi
}

# Function to resolve county name or FIPS code from latitude/longitude or address
resolve_county() {
    local lat="$1"
    local lon="$2"
    local address="$3"

    if [ -n "$lat" ] && [ -n "$lon" ] && [ "$lat" != "N/A" ] && [ "$lon" != "N/A" ]; then
        # Use latitude and longitude to resolve county using the improved function
        get_county_from_coords "$lat" "$lon"
    elif [ -n "$address" ] && [ "$address" != "N/A" ]; then
        # Use address to geocode and then resolve county
        echo "Geocoding address: $address"
        
        # Parse the address into components (simplified approach)
        local encoded_address=$(echo "$address" | jq -sRr @uri)
        local url="https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=${encoded_address}&benchmark=Public_AR_Current&format=json"
        local response=$(curl -s "$url")
        
        # Extract coordinates
        local lat=$(echo "$response" | jq -r '.result.addressMatches[0].coordinates.y')
        local lon=$(echo "$response" | jq -r '.result.addressMatches[0].coordinates.x')
        
        if [[ -z "$lat" || "$lat" == "null" || -z "$lon" || "$lon" == "null" ]]; then
            echo "N/A|N/A"
        else
            # Get county from coordinates
            get_county_from_coords "$lat" "$lon"
        fi
    else
        echo "N/A|N/A"
    fi
}

# Function to process a single state
process_state() {
    local st="$1"
    local output_dir="$2"

    urlstr=$urlbase"/location/"${st,,}"/all"
    ofile="$output_dir/$st.txt"
    det="$output_dir/${st}_details.txt"
    
    echo "Retrieving contents from : $urlstr"
    
    # Use a unique temporary file for each state to avoid conflicts
    temp_file="$output_dir/all_$st"
    
    if [ ! -f "$ofile" ]; then
        wget -q "$urlstr" -O "$temp_file" || handle_error "Failed to retrieve data from $urlstr"
        if [ -f "$temp_file" ]; then
            grep "<li><span> <a href=" "$temp_file" | sed -e 's/^.*<strong>//g' -e 's/:<\/strong>//g' -e 's/<\/a>.*$//g' > "$ofile"
            echo "Saved contents into $ofile"
            rm -f "$temp_file"
        else
            handle_error "Failed to download data for state $st"
        fi
    fi

    # Initialize details file with header
    echo "Attraction_name,Address,Latitude,Longitude,Type_of_attraction,Region,State,County,FIPS,URL" > "$det"

    # Navigate to attraction URL to find address, descriptions etc.
    while IFS="" read -r p || [ -n "$p" ]; do
        attr_suff=$(echo "$p" | sed -e 's/.*<a href="//g' -e 's/">.*//g')
        urlattr=$urlbase$attr_suff

        echo "Processing attraction: $urlattr"
        
        # Extract attraction details
        local attr_page=$(curl -s "$urlattr")
        name=$(echo "$attr_page" | grep -oP '(?<=<h1>).*(?=</h1>)' | sed -e 's/\(.*\)<\/a>//g')
        addr=$(echo "$attr_page" | grep -oP '(?<=Address:).*(?=</a></dd><dt>)' | rev | cut -d'>' -f1 | rev)
        lat=$(echo "$attr_page" | grep -oP '(?<=Latitude:).*(?=</dd><dt>)' | rev | cut -d'>' -f1 | rev)
        lon=$(echo "$attr_page" | grep -oP '(?<=Longitude:).*(?=</dd><dt>)' | rev | cut -d'>' -f1 | rev)
        type=$(echo "$attr_page" | grep -oP '(?<=Type:).*(?=</dd><dt>)' | rev | cut -d'>' -f1 | rev)
        region=$(echo "$attr_page" | grep -oP '(?<=Region:).*(?=</dd><dt>)' | rev | cut -d'>' -f1 | rev)

        # Replace empty fields with "N/A"
        name=${name:-"N/A"}
        addr=${addr:-"N/A"}
        lat=${lat:-"N/A"}
        lon=${lon:-"N/A"}
        type=${type:-"N/A"}
        region=${region:-"N/A"}

        # Resolve county and FIPS code using improved function
        county_fips=$(resolve_county "$lat" "$lon" "$addr")
        county=$(echo "$county_fips" | cut -d'|' -f1)
        fips=$(echo "$county_fips" | cut -d'|' -f2)

        echo "  - Name: $name"
        echo "  - Coords: $lat, $lon"
        echo "  - County: $county (FIPS: $fips)"
        
        echo "\"$name\",\"$addr\",\"$lat\",\"$lon\",\"$type\",\"$region\",\"$st\",\"$county\",\"$fips\",\"$urlattr\"" >> "$det"
    done < "$ofile"
    
    echo "Details file generated: $det"
}

# Parse command-line arguments
while getopts ":o:" opt; do
    case $opt in
        o) output_dir="$OPTARG" ;;
        *) usage ;;
    esac
done

# Check if output directory is provided
if [ -z "$output_dir" ]; then
    handle_error "Output directory not specified. Use -o to specify the output directory."
fi

# Check if wget, curl, and jq are installed
if ! command -v wget &> /dev/null; then
    handle_error "wget is required to run this script."
fi

if ! command -v curl &> /dev/null; then
    handle_error "curl is required to run this script."
fi

if ! command -v jq &> /dev/null; then
    handle_error "jq is required to run this script."
fi

# Create output directory if it doesn't exist
mkdir -p "$output_dir" || handle_error "Failed to create output directory $output_dir"

# Process each state sequentially
for st in "${states[@]}"; do
    process_state "$st" "$output_dir"
done

echo "Processing complete."