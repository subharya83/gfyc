#!/bin/bash
# apt-get install jq

states=('AL' 'AK' 'AZ' 'AR' 'CA' 'CO' 'CT' 'DE' 'DC' 'FL' 'GA' 'HI' 'ID' 'IL' 
 'IN' 'IA' 'KS' 'KY' 'LA' 'ME' 'MD' 'MA' 'MI' 'MN' 'MS' 'MO' 'MT' 'NE' 'NV' 
 'NH' 'NJ' 'NM' 'NY' 'NC' 'ND' 'OH' 'OK' 'OR' 'PA' 'PR' 'RI' 'SC' 'SD' 'TN' 
 'TX' 'UT' 'VT' 'VI' 'VA' 'WA' 'WV' 'WI' 'WY')


urlbase='https://www.roadsideamerica.com/'

# Function to display usage
usage() {
    echo "Usage: $0 -o <output_directory> [-t <threads>]"
    echo "This script retrieves a list of attractions for each state and saves the details into a file."
    echo "Options:"
    echo "  -o <output_directory>  Specify the output directory for saving files."
    echo "  -t <threads>           Specify the number of threads to use for parallel processing."
    exit 1
}

# Function to handle errors
handle_error() {
    echo "Error: $1"
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
    # Output the information in CSV format
    echo "\"$attraction_name\", \"$address\""
}

# Function to get latitude, longitude, county, formatted address, and FIPS code from an address using Google Maps API and FCC API
get_geo_info() {
    local address="$1"
    local api_key="API"  # Replace with your Google Maps API key
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

    # Extract state from Google Maps API response
    local state=$(echo "$response" | jq -r '.results[0].address_components[] | select(.types[] == "administrative_area_level_1") | .short_name')
    state=$(sanitize "$state")

    # Get FIPS code using FCC API
    local fips_code=""
    if [ -n "$latitude" ] && [ -n "$longitude" ]; then
        fips_code=$(curl -s "https://geo.fcc.gov/api/census/block/find?latitude=$latitude&longitude=$longitude&format=json" | jq -r '.County.FIPS')
        fips_code=$(sanitize "$fips_code")
    fi
    # Get unique PlaceID
    local place_id=$(echo "$response" | jq -r '.results[0].place_id')
    # Get global Plus code
    local global_code=$(echo "$response" | jq -r '.results[0].plus_code.global_code')

    echo "\"$place_id\", \"$formatted_address\", \"$county\", \"$state\", \"$latitude\", \"$longitude\", \"$fips_code\", \"$global_code\""
}

# Function to process a single state
process_state() {
    local st="$1"
    local output_dir="$2"
    local urlstr=$urlbase"/location/"${st,,}"/all"
    local ofile="$output_dir/$st.txt"
    local det="$output_dir/${st}_details.txt"
    
    echo "Retrieving contents from : $urlstr"
    
    if [ ! -f "$ofile" ]; then
        wget -q "$urlstr" -O all || handle_error "Failed to retrieve data from $urlstr"
        grep "<li><span> <a href=" all | sed -e 's/^.*<strong>//g' -e 's/:<\/strong>//g' -e 's/<\/a>.*$//g' > "$ofile"
        echo "Saved contents into $ofile"
        rm -f all
    fi

    # Create a temporary file for this state's attractions
    local temp_file="$output_dir/${st}_temp.csv"

    # Navigate to attraction URL to find address, descriptions etc.
    while IFS="" read -r p || [ -n "$p" ]; do
        attr_suff=$(echo "$p" | sed -e 's/.*<a href="//g' -e 's/">.*//g')
        _att_url=$urlbase$attr_suff
        
        # Extract attraction info
        _att=$(extract_attraction_info "$_att_url")
        _att_name=$(echo "$_att" | awk -F'"' '{print $2}')
        echo $_att_name

        _att_addr=$(echo "$_att" | awk -F'"' '{print $4}')
        echo $_att_addr
        
        # Get geo info for the address
        _geo=$(get_geo_info "$_att_addr")
        
        # Append the combined information to the temporary CSV file
        echo "\"$_att_name\",$_geo,\"$_att_url\"" >> "$temp_file"
    done < "$ofile"
    
    echo "Details for state $st have been added to $temp_file"
}

# Parse command-line arguments
while getopts ":o:t:" opt; do
    case $opt in
        o) output_dir="$OPTARG" ;;
        t) threads="$OPTARG" ;;
        *) usage ;;
    esac
done

# Check if output directory is provided
if [ -z "$output_dir" ]; then
    handle_error "Output directory not specified. Use -o to specify the output directory."
fi

# Check if wget, curl, and jq are installed
if ! command -v wget &> /dev/null || ! command -v curl &> /dev/null || ! command -v jq &> /dev/null; then
    handle_error "wget, curl, and jq are required to run this script."
fi

# Create output directory if it doesn't exist
mkdir -p "$output_dir"

# Initialize master CSV file with header
master_csv="$output_dir/attractions.csv"
if [ ! -f "$master_csv" ]; then
    echo "Attraction_name,Place_id,Latitude,Longitude,County,Formatted_address,FIPS,Global_code,URL" > "$master_csv"
fi

# Process states in parallel if threads are specified
if [ -n "$threads" ]; then
    export -f process_state extract_attraction_info get_geo_info sanitize handle_error
    export urlbase output_dir
    printf "%s\n" "${states[@]}" | xargs -I{} -P "$threads" bash -c 'process_state "$@"' _ {}
    
    # Merge all temporary files into the master CSV file
    for st in "${states[@]}"; do
        temp_file="$output_dir/${st}_temp.csv"
        if [ -f "$temp_file" ]; then
            cat "$temp_file" >> "$master_csv"
            rm -f "$temp_file"
        fi
    done
else
    # Process states sequentially
    for st in "${states[@]}"; do
        process_state "$st" "$output_dir"
    done
fi

echo "All attraction details have been compiled into $master_csv"