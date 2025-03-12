#!/bin/bash

# Usage function
usage() {
    echo "Usage: $0 -d <download_directory>"
    echo "  -d  Directory where files will be downloaded"
    exit 1
}

# Check if no arguments are provided
if [ $# -eq 0 ]; then
    usage
fi

# Parse command-line arguments
while getopts ":d:" opt; do
    case ${opt} in
        d)
            DOWNLOAD_DIR=$OPTARG
            ;;
        \?)
            echo "Invalid option: -$OPTARG" 1>&2
            usage
            ;;
        :)
            echo "Invalid option: -$OPTARG requires an argument" 1>&2
            usage
            ;;
    esac
done

# Check if the download directory is provided
if [ -z "$DOWNLOAD_DIR" ]; then
    echo "Error: Download directory not specified."
    usage
fi

# Create the download directory if it doesn't exist
mkdir -p "$DOWNLOAD_DIR"

# Base URL
base_url="https://www.irs.gov/pub/irs-soi"

# Loop over the range of XX values
for XX in {11..21}; do
    # Calculate YY as XX + 1
    YY=$((XX + 1))

    # Construct the file names
    inflow_file="countyinflow${XX}${YY}.csv"
    outflow_file="countyoutflow${XX}${YY}.csv"

    # Construct the full URLs
    inflow_url="${base_url}/${inflow_file}"
    outflow_url="${base_url}/${outflow_file}"

    # Download the files to the specified directory
    wget -P "$DOWNLOAD_DIR" "$inflow_url"
    wget -P "$DOWNLOAD_DIR" "$outflow_url"
done

echo "Files have been downloaded to $DOWNLOAD_DIR"