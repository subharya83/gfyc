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
    echo "Error: $1" >&2
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
    local county_name=$(echo "$response" | jq -r '.result.geographies.Counties[0].NAME' 2>/dev/null)
    local county_fips=$(echo "$response" | jq -r '.result.geographies.Counties[0].GEOID' 2>/dev/null)
    
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
        # Use latitude and longitude to resolve county
        get_county_from_coords "$lat" "$lon"
    elif [ -n "$address" ] && [ "$address" != "N/A" ]; then
        # Simplified address processing to avoid debug output in CSV
        local encoded_address=$(echo "$address" | tr -d '\n' | sed 's/ /%20/g')
        local url="https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=${encoded_address}&benchmark=Public_AR_Current&format=json"
        local response=$(curl -s "$url")
        
        # Extract coordinates
        local lat=$(echo "$response" | jq -r '.result.addressMatches[0].coordinates.y' 2>/dev/null)
        local lon=$(echo "$response" | jq -r '.result.addressMatches[0].coordinates.x' 2>/dev/null)
        
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

# Function to extract HTML content with more reliable patterns
extract_html_content() {
    local html="$1"
    local pattern="$2"
    local default="N/A"
    
    result=$(echo "$html" | grep -oP "$pattern" | head -1 | sed -e 's/<[^>]*>//g' | tr -d '\n' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
    
    if [ -z "$result" ]; then
        echo "$default"
    else
        echo "$result"
    fi
}

# Function to sanitize data for CSV
sanitize_for_csv() {
    local input="$1"
    # Escape double quotes and wrap in quotes
    echo "\"$(echo "$input" | sed 's/"/""/g')\""
}

# Function to process a single state
process_state() {
    local st="$1"
    local output_dir="$2"

    urlstr=$urlbase"/location/"${st,,}"/all"
    ofile="$output_dir/$st.txt"
    det="$output_dir/${st}_details.txt"
    
    echo "Retrieving contents from: $urlstr"
    
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
        
        # Get the whole page content at once
        local attr_page=$(curl -s "$urlattr")
        
        # Extract data with more reliable patterns
        name=$(extract_html_content "$attr_page" '(?<=<h1>).*?(?=</h1>)' | sed -e 's/<[^>]*>//g')
        
        # Extract address from the details section
        addr=$(extract_html_content "$attr_page" '(?s)<dt>Address:</dt>\s*<dd>.*?</dd>' | sed -e 's/<dt>Address:<\/dt>//g' -e 's/<dd>//g' -e 's/<\/dd>//g' -e 's/<a[^>]*>//g' -e 's/<\/a>//g')
        
        # Extract latitude and longitude
        lat=$(extract_html_content "$attr_page" '(?s)<dt>Latitude:</dt>\s*<dd>.*?</dd>' | sed -e 's/<dt>Latitude:<\/dt>//g' -e 's/<dd>//g' -e 's/<\/dd>//g')
        lon=$(extract_html_content "$attr_page" '(?s)<dt>Longitude:</dt>\s*<dd>.*?</dd>' | sed -e 's/<dt>Longitude:<\/dt>//g' -e 's/<dd>//g' -e 's/<\/dd>//g')
        
        # Extract type and region
        type=$(extract_html_content "$attr_page" '(?s)<dt>Type:</dt>\s*<dd>.*?</dd>' | sed -e 's/<dt>Type:<\/dt>//g' -e 's/<dd>//g' -e 's/<\/dd>//g')
        region=$(extract_html_content "$attr_page" '(?s)<dt>Region:</dt>\s*<dd>.*?</dd>' | sed -e 's/<dt>Region:<\/dt>//g' -e 's/<dd>//g' -e 's/<\/dd>//g')

        # Default values if not found
        name=${name:-"N/A"}
        addr=${addr:-"N/A"}
        lat=${lat:-"N/A"}
        lon=${lon:-"N/A"}
        type=${type:-"N/A"}
        region=${region:-"N/A"}

        # Get county info silently (suppress debug output)
        county_info=$(resolve_county "$lat" "$lon" "$addr" 2>/dev/null)
        county=$(echo "$county_info" | cut -d'|' -f1)
        fips=$(echo "$county_info" | cut -d'|' -f2)

        # Sanitize all fields for CSV output
        name_csv=$(sanitize_for_csv "$name")
        addr_csv=$(sanitize_for_csv "$addr")
        lat_csv=$(sanitize_for_csv "$lat")
        lon_csv=$(sanitize_for_csv "$lon")
        type_csv=$(sanitize_for_csv "$type")
        region_csv=$(sanitize_for_csv "$region")
        county_csv=$(sanitize_for_csv "$county")
        fips_csv=$(sanitize_for_csv "$fips")
        url_csv=$(sanitize_for_csv "$urlattr")

        echo "  - Name: $name"
        echo "  - Address: $addr"
        echo "  - Coords: $lat, $lon"
        echo "  - County: $county (FIPS: $fips)"
        
        # Write to CSV file with proper formatting
        echo "$name_csv,$addr_csv,$lat_csv,$lon_csv,$type_csv,$region_csv,\"$st\",$county_csv,$fips_csv,$url_csv" >> "$det"
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