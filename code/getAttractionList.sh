#!/bin/bash
# apt-get install jq

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

# Function to resolve county name or FIPS code from latitude/longitude or address
resolve_county() {
    local lat="$1"
    local lon="$2"
    local address="$3"

    if [ -n "$lat" ] && [ -n "$lon" ]; then
        # Use latitude and longitude to resolve county
        county=$(curl -s "https://geo.fcc.gov/api/census/block/find?latitude=$lat&longitude=$lon&format=json" | jq -r '.County.name')
        fips=$(curl -s "https://geo.fcc.gov/api/census/block/find?latitude=$lat&longitude=$lon&format=json" | jq -r '.County.FIPS')
    elif [ -n "$address" ]; then
        # Use address to resolve county (requires geocoding API)
        echo "Address-based county resolution is not implemented in this script."
        county=""
        fips=""
    else
        echo "No valid input provided for county resolution."
        county=""
        fips=""
    fi

    echo "$county|$fips"
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
if ! command -v wget &> /dev/null || ! command -v curl &> /dev/null || ! command -v jq &> /dev/null; then
    handle_error "wget, curl, and jq are required to run this script."
fi

# Create output directory if it doesn't exist
mkdir -p "$output_dir"

# Obtain list of attractions for states
for st in "${states[@]}"; do
    urlstr=$urlbase"/location/"${st,,}"/all"
    ofile="$output_dir/$st.txt"
    det="$output_dir/${st}_details.txt"
    
    echo "Retrieving contents from : $urlstr"
    
    if [ ! -f "$ofile" ]; then
        wget -q "$urlstr" -O all || handle_error "Failed to retrieve data from $urlstr"
        grep "<li><span> <a href=" all | sed -e 's/^.*<strong>//g' -e 's/:<\/strong>//g' -e 's/<\/a>.*$//g' > "$ofile"
        echo "Saved contents into $ofile"
        rm -f all
    fi

    # Initialize details file with header
    echo "Attraction_name,Address,Latitude,Longitude,Type_of_attraction,Region,State,County,FIPS,URL" > "$det"

    # Navigate to attraction URL to find address, descriptions etc.
    while IFS="" read -r p || [ -n "$p" ]; do
        attr_suff=$(echo "$p" | sed -e 's/.*<a href="//g' -e 's/">.*//g')
        urlattr=$urlbase$attr_suff

        name=$(curl -s "$urlattr" | grep -oP '(?<=<h1>).*(?=</h1>)' | sed -e 's/\(.*\)<\/a>//g')
        addr=$(curl -s "$urlattr" | grep -oP '(?<=Address:).*(?=</a></dd><dt>)' | rev | cut -d'>' -f1 | rev)
        lat=$(curl -s "$urlattr" | grep -oP '(?<=Latitude:).*(?=</dd><dt>)' | rev | cut -d'>' -f1 | rev)
        lon=$(curl -s "$urlattr" | grep -oP '(?<=Longitude:).*(?=</dd><dt>)' | rev | cut -d'>' -f1 | rev)
        type=$(curl -s "$urlattr" | grep -oP '(?<=Type:).*(?=</dd><dt>)' | rev | cut -d'>' -f1 | rev)
        region=$(curl -s "$urlattr" | grep -oP '(?<=Region:).*(?=</dd><dt>)' | rev | cut -d'>' -f1 | rev)

        # Resolve county and FIPS code
        county_fips=$(resolve_county "$lat" "$lon" "$addr")
        county=$(echo "$county_fips" | cut -d'|' -f1)
        fips=$(echo "$county_fips" | cut -d'|' -f2)

        echo "\"$name\",\"$addr\",\"$lat\",\"$lon\",\"$type\",\"$region\",\"$st\",\"$county\",\"$fips\",\"$urlattr\"" | tee -a "$det"
    done < "$ofile"
    
    echo "Details file generated $det"
done